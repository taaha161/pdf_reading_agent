"""LangChain agent: extract transactions from statement text and categorize them."""
import json
import logging
import os
import re
import time
from typing import Any

from langchain_core.prompts import ChatPromptTemplate

logger = logging.getLogger("statement_agent")
from langchain_core.output_parsers import StrOutputParser

# Prefer Groq (free tier); fallback to Ollama if GROQ_API_KEY not set
try:
    from langchain_groq import ChatGroq
    _GROQ_AVAILABLE = True
except ImportError:
    _GROQ_AVAILABLE = False
from langchain_community.chat_models import ChatOllama

CATEGORIES = [
    "Groceries",
    "Utilities",
    "Shopping",
    "Transfer",
    "Dining",
    "Transport",
    "Healthcare",
    "Entertainment",
    "Other",
]

CATEGORY_GUIDANCE = """
Use the FULL description and all transaction details to choose the category:
- Groceries: supermarkets, food stores, grocery delivery (e.g. Walmart grocery, Safeway, Whole Foods).
- Utilities: electric, gas, water, internet, phone, cable, streaming subscriptions for household services.
- Shopping: retail, online stores, marketplaces (e.g. Amazon, eBay), clothing, general merchandise.
- Transfer: bank transfers, wire, ACH, Venmo/PayPal transfers, internal moves between accounts.
- Dining: restaurants, cafes, fast food, bars, food delivery (e.g. Uber Eats, DoorDash), coffee shops.
- Transport: fuel/gas stations, tolls, parking, ride-share (Uber/Lyft), public transit, car maintenance.
- Healthcare: doctors, pharmacy, hospital, insurance, medical bills, prescriptions.
- Entertainment: streaming (Netflix, Spotify), movies, games, events, hobbies.
- Other: anything that does not clearly fit above; use only when uncertain.
Read the entire description and any reference/memo text to infer the merchant or purpose, then categorize.
"""

# Max chars of statement text to send to extraction LLM in one go (raise if table still misses later months)
EXTRACTION_TEXT_CAP = 100000
EXTRACTION_CHUNK_OVERLAP = 3000  # overlap when chunking so we don't cut a transaction in half


def _get_llm():
    api_key = os.environ.get("GROQ_API_KEY")
    if api_key and _GROQ_AVAILABLE:
        # max_tokens=8192 so extraction/categorization can return full transaction list (default can truncate at ~Apr)
        return ChatGroq(model="llama-3.1-8b-instant", api_key=api_key, temperature=0, max_tokens=8192)
    return ChatOllama(model="llama3.2", temperature=0)


def _format_transactions_for_categorization(transactions: list[dict]) -> str:
    """Format each transaction with full context so the model can read description and all details."""
    lines = []
    for i, t in enumerate(transactions):
        lines.append(
            f"[{i + 1}] date: {t.get('date', '')} | description: {t.get('description', '')} | "
            f"amount: {t.get('amount', '')} | type: {t.get('type', '')}"
        )
    return "\n".join(lines)


def _extract_json_block(text: str) -> str:
    """Try to get a JSON array or object from LLM output."""
    # Match [...] or {...}
    for pattern in [r"\[[\s\S]*\]", r"\{[\s\S]*\}"]:
        m = re.search(pattern, text)
        if m:
            return m.group(0)
    return text


def _extract_first_json_array(text: str) -> str:
    """Extract the first complete JSON array by bracket matching (handles 'Extra data' when LLM appends text)."""
    start = text.find("[")
    if start == -1:
        return ""
    depth = 0
    in_string = False
    escape = False
    quote = None
    for i in range(start, len(text)):
        c = text[i]
        if escape:
            escape = False
            continue
        if c == "\\" and in_string:
            escape = True
            continue
        if in_string:
            if c == quote:
                in_string = False
            continue
        if c in ('"', "'"):
            in_string = True
            quote = c
            continue
        if c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return text[start:]


def _extract_first_json_object(text: str, start_pos: int = 0) -> tuple[str, int] | None:
    """Extract the first complete JSON object {...} starting at start_pos. Returns (substring, end_index) or None."""
    start = text.find("{", start_pos)
    if start == -1:
        return None
    depth = 0
    in_string = False
    escape = False
    quote = None
    for i in range(start, len(text)):
        c = text[i]
        if escape:
            escape = False
            continue
        if c == "\\" and in_string:
            escape = True
            continue
        if in_string:
            if c == quote:
                in_string = False
            continue
        if c in ('"', "'"):
            in_string = True
            quote = c
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return (text[start : i + 1], i + 1)
    return None


def _parse_transaction_objects_from_text(text: str) -> list[dict]:
    """When full JSON array parse fails, extract individual {...} objects and parse; return list of transaction-like dicts."""
    result = []
    pos = 0
    while True:
        obj = _extract_first_json_object(text, pos)
        if obj is None:
            break
        sub, next_pos = obj
        pos = next_pos
        try:
            d = json.loads(sub)
            if not isinstance(d, dict):
                continue
            if "amount" in d or ("date" in d and "description" in d):
                result.append(d)
        except json.JSONDecodeError:
            continue
    return result


def extract_and_categorize(raw_text: str) -> list[dict[str, Any]]:
    """
    Extract transactions from raw statement text, then assign categories.
    Returns list of dicts with keys: date, description, amount, type, category.
    """
    if not raw_text or not raw_text.strip():
        return []

    t0 = time.perf_counter()
    llm = _get_llm()
    logger.info("extract_and_categorize: start, text len=%d", len(raw_text))

    extract_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a precise assistant. Extract every bank transaction from the given statement text. "
                "Return ONLY a valid JSON array of objects. Each object must have: "
                '"date" (string), "description" (string), "amount" (string, e.g. 123.45), "type" (string: "credit" or "debit"). '
                "Preserve the FULL description exactly as shown: include merchant name, location, reference numbers, "
                "memo lines, and any other text that appears for that transaction. Do not shorten or summarize descriptions. "
                "IMPORTANT: Extract ONLY actual transactions (rows that have a date, a description, and a debit or credit amount). "
                "Do NOT include: Opening Balance, Closing Balance, Balance B/F, Balance C/F, running balance lines; "
                "rows that are only a balance figure; header rows; summary/total lines that are just a balance. "
                "If no transactions are found, return [].",
            ),
            ("human", "{text}"),
        ]
    )
    chain = extract_prompt | llm | StrOutputParser()
    t1 = time.perf_counter()
    text_trimmed = raw_text.strip()
    # Chunk long statements so we don't truncate (e.g. table showed only till March when last tx was June)
    if len(text_trimmed) <= EXTRACTION_TEXT_CAP:
        chunks = [text_trimmed]
    else:
        chunks = []
        start = 0
        while start < len(text_trimmed):
            end = start + EXTRACTION_TEXT_CAP
            chunks.append(text_trimmed[start:end])
            if end >= len(text_trimmed):
                break
            start = end - EXTRACTION_CHUNK_OVERLAP
        logger.info("extract_and_categorize: text len=%d, splitting into %d chunks", len(text_trimmed), len(chunks))
    all_transactions = []
    for chunk_idx, text_input in enumerate(chunks):
        logger.info("extract_and_categorize: calling LLM for transaction extraction (chunk %d/%d, len=%d)...", chunk_idx + 1, len(chunks), len(text_input))
        out = chain.invoke({"text": text_input})
        logger.info("extract_and_categorize: extraction LLM done (%.2f s)", time.perf_counter() - t1)
        json_str = _extract_json_block(out)
        try:
            chunk_tx = json.loads(json_str)
        except json.JSONDecodeError:
            chunk_tx = []
        if isinstance(chunk_tx, list):
            all_transactions.extend(chunk_tx)
        t1 = time.perf_counter()
    # Dedupe by (date, description, amount) in case overlap created duplicates
    seen = set()
    transactions = []
    for t in all_transactions:
        if not isinstance(t, dict):
            continue
        key = (str(t.get("date", "")), str(t.get("description", "")), str(t.get("amount", "")))
        if key in seen:
            continue
        seen.add(key)
        transactions.append(t)
    if len(chunks) > 1 and all_transactions:
        logger.info("extract_and_categorize: merged %d chunks -> %d unique transactions", len(chunks), len(transactions))

    if not transactions or not isinstance(transactions, list):
        transactions = []

    # Fallback: if we got 0 transactions but there's substantial text (e.g. from vision), try a simpler direct prompt
    if len(transactions) == 0 and len(text_trimmed) > 400:
        logger.info("extract_and_categorize: 0 transactions, trying fallback extraction (text len=%d)", len(text_trimmed))
        fallback_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You extract bank transactions from text. Return ONLY a JSON array. Each element is an object with: "
                    '"date", "description", "amount", "type" (use "debit" or "credit"). '
                    "Do NOT include: Opening Balance, Closing Balance, Balance B/F, Balance C/F, or any balance-only row. "
                    "Find every actual transaction (date, description, money amount). Output nothing but the JSON array.",
                ),
                ("human", "{text}"),
            ]
        )
        fallback_chain = fallback_prompt | llm | StrOutputParser()
        fallback_input = text_trimmed[:EXTRACTION_TEXT_CAP]
        try:
            fallback_out = fallback_chain.invoke({"text": fallback_input})
            fallback_json = _extract_first_json_array(fallback_out)
            if not fallback_json:
                fallback_json = _extract_json_block(fallback_out)
            fallback_list = json.loads(fallback_json)
            if isinstance(fallback_list, list) and len(fallback_list) > 0:
                transactions = fallback_list
                logger.info("extract_and_categorize: fallback extracted %d transactions", len(transactions))
        except json.JSONDecodeError:
            objs = _parse_transaction_objects_from_text(fallback_out)
            if objs:
                transactions = objs
                logger.info("extract_and_categorize: fallback parsed %d transactions from objects", len(transactions))
        except Exception as e:
            logger.warning("extract_and_categorize: fallback extraction failed: %s", e)

    if not transactions or not isinstance(transactions, list):
        return []

    # Ensure each item has required keys
    normalized = []
    for t in transactions:
        if not isinstance(t, dict):
            continue
        normalized.append({
            "date": str(t.get("date", "")),
            "description": str(t.get("description", "")),
            "amount": str(t.get("amount", "")),
            "type": str(t.get("type", "debit")).lower() in ("credit", "cr") and "credit" or "debit",
            "category": "",  # filled below
        })
    transactions = normalized
    logger.info("extract_and_categorize: extracted %d transactions, starting categorization...", len(transactions))

    # Categorize using full context (description and all fields) per transaction
    categories_str = ", ".join(CATEGORIES)
    # Format so the model sees full context for each transaction
    transactions_context = _format_transactions_for_categorization(transactions)
    cat_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You categorize bank transactions. For each transaction you must assign exactly one category from this list: "
                f"{categories_str}. "
                + CATEGORY_GUIDANCE
                + " Return ONLY a valid JSON array of objects. Each object must have: date, description, amount, type, category. "
                "Keep date, description, amount, and type exactly as given; only set category based on the full context.",
            ),
            (
                "human",
                "Categorize each of these transactions by reading the entire description and any other info:\n\n"
                "{transactions_context}\n\n"
                "Return the same list as a JSON array, with category set for each transaction.",
            ),
        ]
    )
    cat_chain = cat_prompt | llm | StrOutputParser()
    t2 = time.perf_counter()
    logger.info("extract_and_categorize: calling LLM for categorization...")
    cat_out = cat_chain.invoke({"transactions_context": transactions_context})
    logger.info("extract_and_categorize: categorization LLM done (%.2f s)", time.perf_counter() - t2)
    cat_json_str = _extract_json_block(cat_out)
    try:
        categorized = json.loads(cat_json_str)
    except json.JSONDecodeError:
        categorized = []
    if not isinstance(categorized, list):
        categorized = []

    # Match by index or by description+amount to assign categories
    for i, t in enumerate(transactions):
        transactions[i]["category"] = "Other"
    for i, c in enumerate(categorized):
        if not isinstance(c, dict) or "category" not in c:
            continue
        cat = str(c.get("category", "")).strip()
        if cat not in CATEGORIES:
            # Try matching to a category (e.g. "Groceries" vs "groceries")
            for allowed in CATEGORIES:
                if allowed.lower() == cat.lower():
                    cat = allowed
                    break
            else:
                cat = "Other"
        if i < len(transactions):
            transactions[i]["category"] = cat
        else:
            # Match by description+amount if list lengths differ
            desc = str(c.get("description", "")).strip()
            amt = str(c.get("amount", "")).strip()
            for j, t in enumerate(transactions):
                if t.get("description", "").strip() == desc and str(t.get("amount", "")).strip() == amt:
                    transactions[j]["category"] = cat
                    break

    logger.info("extract_and_categorize: done, %d transactions (%.2f s total)", len(transactions), time.perf_counter() - t0)
    return transactions
