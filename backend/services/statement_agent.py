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


def _get_llm():
    api_key = os.environ.get("GROQ_API_KEY")
    if api_key and _GROQ_AVAILABLE:
        return ChatGroq(model="llama-3.1-8b-instant", api_key=api_key, temperature=0)
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
                "If no transactions are found, return [].",
            ),
            ("human", "{text}"),
        ]
    )
    chain = extract_prompt | llm | StrOutputParser()
    t1 = time.perf_counter()
    logger.info("extract_and_categorize: calling LLM for transaction extraction...")
    out = chain.invoke({"text": raw_text[:12000]})  # cap length
    logger.info("extract_and_categorize: extraction LLM done (%.2f s)", time.perf_counter() - t1)
    json_str = _extract_json_block(out)
    try:
        transactions = json.loads(json_str)
    except json.JSONDecodeError:
        transactions = []

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
