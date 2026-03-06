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

# Prefer Gemini when GOOGLE_GEMINI_API_KEY is set; fallback to Ollama otherwise
try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    _GEMINI_AVAILABLE = True
except ImportError:
    _GEMINI_AVAILABLE = False
from langchain_community.chat_models import ChatOllama

CATEGORIES = [
    "Income",
    "Transfer",
    "Rent & Mortgage",
    "Utilities",
    "Groceries",
    "Dining",
    "Shopping",
    "Transport",
    "Healthcare",
    "Insurance",
    "Subscriptions",
    "Entertainment",
    "Travel",
    "Fees & Charges",
    "Education",
    "Charity & Donations",
    "Savings & Investments",
    "Tax & Government",
    "Other",
]

CATEGORY_GUIDANCE = """
Use the FULL description, reference, and memo to infer merchant or purpose. Pick exactly one category. Prefer the most specific match; use Other only when nothing else fits.

- Income: salary, wages, direct deposit, refunds (merchant or tax), interest earned, dividends, benefits, pension, freelance/client payments.
- Transfer: moving money between own accounts, wire/ACH to self, Venmo/PayPal/Cash App when it is a transfer (not a purchase), standing order to own account, internal bank transfer.
- Rent & Mortgage: rent, mortgage payment, housing association, landlord, lease payment.
- Utilities: electric, gas, water, sewer, council tax (if listed as utility), internet, landline/mobile phone bill, cable/satellite TV.
- Groceries: supermarkets, grocery delivery (e.g. Instacart, Ocado), food stores, butchers, bakers (food for home).
- Dining: restaurants, cafes, fast food, takeaways, food delivery (Uber Eats, Deliveroo), bars, pubs, coffee shops (eating out).
- Shopping: retail, online stores (Amazon, eBay, Etsy), clothing, electronics, household goods, marketplaces, general merchandise. Use when paying a merchant for goods (not food-at-home, not services above).
- Transport: fuel/petrol, tolls, congestion charge, parking, ride-share (Uber, Lyft, Bolt), taxis, public transit, car maintenance/repair, MOT, vehicle tax.
- Healthcare: doctors, dentist, pharmacy, hospital, clinic, health insurance premium, medical bills, prescriptions, optician, physiotherapy.
- Insurance: car insurance, home/contents insurance, life insurance, travel insurance — any non-health insurance premium.
- Subscriptions: streaming (Netflix, Spotify, Disney+), software (Microsoft 365, Adobe), gym, membership fees, recurring digital services.
- Entertainment: cinema, concerts, events, games (one-off purchases), hobbies, sports events, books (leisure), one-off entertainment spend.
- Travel: flights, hotels, accommodation, car hire, travel agencies, holiday bookings, visa fees for travel.
- Fees & Charges: bank fees, account fees, ATM fees, overdraft fees, late payment fees, penalty charges, card fees.
- Education: tuition, school/uni fees, courses, textbooks, student loan repayment, tutoring.
- Charity & Donations: donations to charity, church, NGO, fundraising, tips (if clearly donation).
- Savings & Investments: transfer to savings account, ISA, investment account, pension contribution (if separate from salary), stock purchase.
- Tax & Government: tax payments (income, council, VAT), fines, court fees, government charges, HMRC, IRS.
- Other: only when the transaction clearly does not fit any of the above; avoid overusing.
"""

# Max chars of statement text to send to extraction LLM in one go (raise if table still misses later months)
EXTRACTION_TEXT_CAP = 100000
EXTRACTION_CHUNK_OVERLAP = 3000  # overlap when chunking so we don't cut a transaction in half


def _get_llm():
    api_key = os.environ.get("GOOGLE_GEMINI_API_KEY")
    if api_key and _GEMINI_AVAILABLE:
        # Use production Flash model for speed and availability; preview models (e.g. gemini-3-flash-preview) are often slow and return 503 under load.
        return ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=api_key,
            temperature=0,
            max_output_tokens=32768,
        )
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
    """Try to get a JSON array or object from LLM output. Strips markdown code fences (e.g. ```json ... ```) first."""
    cleaned = text.strip()
    # Strip ```json ... ``` or ``` ... ``` so we parse even when the model wraps JSON in code blocks
    for marker in ("```json", "```"):
        if cleaned.startswith(marker):
            end = cleaned.find("```", len(marker))
            if end != -1:
                cleaned = cleaned[len(marker) : end].strip()
            break
    # Match [...] or {...}
    for pattern in [r"\[[\s\S]*\]", r"\{[\s\S]*\}"]:
        m = re.search(pattern, cleaned)
        if m:
            return m.group(0)
    return cleaned


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


def _parse_currency_from_response(response_text: str) -> str | None:
    """Parse a line like 'CURRENCY: GBP' or 'CURRENCY: UNKNOWN' from the model response (after the JSON)."""
    if not response_text:
        return None
    for line in response_text.splitlines():
        line = line.strip()
        if line.upper().startswith("CURRENCY:"):
            code = line[9:].strip()
            if not code or code.upper() == "UNKNOWN":
                return None
            return code
    return None


def _infer_currency_fallback(raw_text: str, llm) -> str | None:
    """Fallback: infer currency via a separate LLM call (used only when combined response had no currency)."""
    if not raw_text or len(raw_text.strip()) < 50:
        return None
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Identify the currency from bank statement text (Currency field, symbols, phrases). Reply with ONLY the currency code (USD, PKR, GBP, etc.) or UNKNOWN. No other text.",
            ),
            ("human", "{text}"),
        ]
    )
    try:
        out = (prompt | llm | StrOutputParser()).invoke({"text": raw_text.strip()[:6000]})
        code = (out or "").strip().upper()
        if not code or code == "UNKNOWN":
            return None
        return (out or "").strip()
    except Exception as e:
        logger.warning("_infer_currency_fallback failed: %s", e)
        return None


def extract_and_categorize(raw_text: str) -> tuple[list[dict[str, Any]], str | None]:
    """
    Extract transactions from raw statement text and assign categories in a single LLM call.
    Also infers currency from the same response. Returns (transactions, currency or None).
    Fallback: if 0 transactions, retry with extract-only then categorize (2 calls).
    """
    if not raw_text or not raw_text.strip():
        return [], None

    t0 = time.perf_counter()
    llm = _get_llm()
    text_trimmed = raw_text.strip()
    logger.info("extract_and_categorize: start, text len=%d", len(text_trimmed))

    categories_str = ", ".join(CATEGORIES)
    combined_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a precise assistant. The input is MARKDOWN from a bank statement (e.g. Datalab PDF conversion). "
                "It often contains markdown tables with columns: Date, Value Date, Description, Debit, Credit, Balance. "
                "Task: (1) Extract EVERY transaction row from every such table. (2) For each transaction assign exactly one category from this list: "
                f"{categories_str}. "
                + CATEGORY_GUIDANCE
                + " For each data row: use Date for \"date\", Description for \"description\" (preserve exactly). "
                "If Credit column has a non-zero value use type \"credit\" and amount as that value; if Debit has non-zero use type \"debit\" and amount as absolute value. Ignore Balance. "
                "EXCLUDE: Opening Balance, Closing Balance, summary/footer tables (Total Deposit, End Of Statement), header rows. "
                "Output format: First, a valid JSON array of objects. Each object must have: \"date\", \"description\", \"amount\", \"type\" (\"credit\" or \"debit\"), \"category\" (one of the list above). "
                "Output the complete array—no truncation. Then on the next line write exactly: CURRENCY: <currency code e.g. USD PKR GBP or UNKNOWN if not found in the statement>. "
                "If no transactions are found, output [] then CURRENCY: UNKNOWN.",
            ),
            ("human", "Extract and categorize all transactions from this bank statement markdown. Output the JSON array then a line CURRENCY: ...\n\n{text}"),
        ]
    )
    chain = combined_prompt | llm | StrOutputParser()

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

    all_transactions: list[dict] = []
    currency: str | None = None
    for chunk_idx, text_input in enumerate(chunks):
        logger.info("extract_and_categorize: single-call extract+categorize+currency (chunk %d/%d)...", chunk_idx + 1, len(chunks))
        t1 = time.perf_counter()
        out = chain.invoke({"text": text_input})
        logger.info("extract_and_categorize: LLM done (%.2f s)", time.perf_counter() - t1)
        json_str = _extract_json_block(out)
        # Parse currency from the rest of the response (after the JSON)
        if not currency:
            rest = out.replace(json_str, "", 1).strip() if json_str else out
            currency = _parse_currency_from_response(rest)
        try:
            chunk_tx = json.loads(json_str)
        except json.JSONDecodeError:
            chunk_tx = []
        if isinstance(chunk_tx, list):
            all_transactions.extend(chunk_tx)

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
        logger.info("extract_and_categorize: merged %d chunks -> %d unique", len(chunks), len(transactions))

    if not transactions:
        transactions = []

    # Fallback: 0 transactions — try extract-only then categorize (2 calls)
    if len(transactions) == 0 and len(text_trimmed) > 400:
        logger.info("extract_and_categorize: 0 transactions, trying fallback (extract then categorize)")
        fallback_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "The input is markdown from a bank statement with tables (Date, Description, Debit, Credit). "
                    "Extract EVERY transaction row: date, description, amount, type (\"credit\" or \"debit\"). Skip Opening/Closing balance and summary rows. Return ONLY a JSON array.",
                ),
                ("human", "{text}"),
            ]
        )
        fallback_out = ""
        try:
            fallback_out = (fallback_prompt | llm | StrOutputParser()).invoke({"text": text_trimmed[:EXTRACTION_TEXT_CAP]})
            fallback_json = _extract_first_json_array(fallback_out) or _extract_json_block(fallback_out)
            fallback_list = json.loads(fallback_json)
            if isinstance(fallback_list, list) and fallback_list:
                transactions = [dict(t) for t in fallback_list]
        except (json.JSONDecodeError, Exception) as e:
            objs = _parse_transaction_objects_from_text(fallback_out) if fallback_out else []
            if objs:
                transactions = objs
            else:
                logger.warning("extract_and_categorize: fallback failed: %s", e)
        if transactions:
            for t in transactions:
                if not isinstance(t, dict):
                    continue
                t.setdefault("category", "Other")
            cat_prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", f"Assign each transaction exactly one category from: {categories_str}. " + CATEGORY_GUIDANCE + " Return ONLY a JSON array of objects with date, description, amount, type, category."),
                    ("human", "Categorize:\n{transactions_context}"),
                ]
            )
            ctx = _format_transactions_for_categorization(transactions)
            try:
                cat_out = (cat_prompt | llm | StrOutputParser()).invoke({"transactions_context": ctx})
                categorized = json.loads(_extract_json_block(cat_out))
                if isinstance(categorized, list):
                    for i, c in enumerate(categorized):
                        if i < len(transactions) and isinstance(c, dict) and "category" in c:
                            cat = str(c.get("category", "")).strip()
                            transactions[i]["category"] = cat if cat in CATEGORIES else next((a for a in CATEGORIES if a.lower() == cat.lower()), "Other")
            except Exception:
                pass
            if not currency:
                currency = _infer_currency_fallback(text_trimmed, llm)

    # Normalize: ensure category in CATEGORIES, type is credit/debit
    normalized = []
    for t in transactions:
        if not isinstance(t, dict):
            continue
        cat = str(t.get("category", "")).strip()
        if cat not in CATEGORIES:
            cat = next((a for a in CATEGORIES if a.lower() == cat.lower()), "Other")
        normalized.append({
            "date": str(t.get("date", "")),
            "description": str(t.get("description", "")),
            "amount": str(t.get("amount", "")),
            "type": "credit" if str(t.get("type", "")).lower() in ("credit", "cr") else "debit",
            "category": cat,
        })
    transactions = normalized
    logger.info("extract_and_categorize: done, %d transactions, currency=%s (%.2f s total)", len(transactions), currency or "none", time.perf_counter() - t0)
    return transactions, currency
