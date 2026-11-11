"""Chat service: answer questions about a job's transactions using Gemini, grounded in the same
rows and numbers the results table and summary table show.

Grounding:
- The model gets every transaction (numbered as in the results table), not a truncated CSV.
- It gets the exact totals the UI shows (credits/debits, summary by category), computed in Python.
- Any other count or sum (a person, a month, a keyword, a type) comes from the query_transactions
  tool, which filters and sums in Python, so the model never does arithmetic over rows itself.
"""
import os
import re
from typing import Any

from google import genai
from google.genai.types import AutomaticFunctionCallingConfig, GenerateContentConfig

from services.csv_export import transactions_to_csv
from services.summary import _parse_amount, _summary_by_category

CHAT_MODEL = "gemini-2.5-flash"
# Statement CSV sent in the prompt; ~1,100 rows is ~120k chars, far below the model's context.
MAX_CSV_CHARS = 400_000
QUERY_MAX_ROWS = 200
MAX_TOOL_CALLS = 8

SYSTEM_INSTRUCTION = """You answer questions about ONE bank statement that the user is looking at in a results table and a summary table.

Ground rules:
- Use ONLY the statement data provided. Never invent transactions, names, dates or amounts.
- NEVER add up, count or average amounts yourself. Every number in your answer must be copied from the
  OFFICIAL TOTALS section or from a query_transactions result. For anything not in OFFICIAL TOTALS
  (a person, a month, a keyword, credits only, a date range...), call query_transactions and use its
  "count", "credit_total", "debit_total" and "net".
- Amounts are always positive; "type" says the direction: credit = money added to the account,
  debit = money deducted. Say "received"/"sent" (or credit/debit) explicitly.
- Rows are numbered (#) by their position in the results table (1 = first row), so you may cite them, e.g. "row #12".
- When asked why a row has a category, explain from its description.
- If query_transactions returns more than one entry in "by_category" (e.g. a person paid by bank transfer
  AND Raast), always state the total AND list each category's count and amount from "by_category", so every
  figure can be matched to the summary table.
- If the data cannot answer the question, say so plainly instead of guessing.
- Use the statement currency when showing amounts. Be concise; use a short list or table when listing rows.
"""


def _get_client() -> genai.Client:
    api_key = os.environ.get("GOOGLE_GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "GOOGLE_GEMINI_API_KEY is not set. Set it in .env for chat and extraction."
        )
    return genai.Client(api_key=api_key)


def _norm(s: Any) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip().lower()


def _is_debit(t: dict) -> bool:
    return str(t.get("type", "")).lower() == "debit"


def _money(x: float) -> float:
    return round(x, 2)


def official_totals(transactions: list[dict]) -> dict[str, Any]:
    """The numbers shown in the UI: credits/debits rows and the summary-by-category table."""
    credit = sum(abs(_parse_amount(t.get("amount"))) for t in transactions if not _is_debit(t))
    debit = sum(abs(_parse_amount(t.get("amount"))) for t in transactions if _is_debit(t))
    counts: dict[str, int] = {}
    for t in transactions:
        cat = str(t.get("category", "")).strip() or "Other"
        counts[cat] = counts.get(cat, 0) + 1
    return {
        "transaction_count": len(transactions),
        "credit_count": sum(1 for t in transactions if not _is_debit(t)),
        "debit_count": sum(1 for t in transactions if _is_debit(t)),
        "credits_total_money_in": _money(credit),
        "debits_total_money_out": _money(debit),
        "net_credits_minus_debits": _money(credit - debit),
        "summary_by_category": [
            {"category": c, "summary_total": _money(total), "transactions": counts.get(c, 0)}
            for c, total in _summary_by_category(transactions)
        ],
    }


def query_rows(
    transactions: list[dict],
    category: str = "",
    category_contains: str = "",
    description_contains: str = "",
    date_contains: str = "",
    type: str = "",
) -> dict[str, Any]:
    """Filter rows (all filters ANDed, case-insensitive) and return exact count and sums."""
    cat_eq, cat_in, desc_in, date_in = _norm(category), _norm(category_contains), _norm(description_contains), _norm(date_contains)
    want_type = _norm(type)
    matched = []
    for i, t in enumerate(transactions, start=1):
        cat = _norm(t.get("category")) or "other"
        if cat_eq and cat != cat_eq:
            continue
        if cat_in and cat_in not in cat:
            continue
        if desc_in and desc_in not in _norm(t.get("description")):
            continue
        if date_in and date_in not in _norm(t.get("date")):
            continue
        if want_type in ("credit", "debit") and str(t.get("type", "")).lower() != want_type:
            continue
        matched.append((i, t))
    credit = sum(abs(_parse_amount(t.get("amount"))) for _, t in matched if not _is_debit(t))
    debit = sum(abs(_parse_amount(t.get("amount"))) for _, t in matched if _is_debit(t))
    by_category: dict[str, dict[str, Any]] = {}
    for _, t in matched:
        b = by_category.setdefault(str(t.get("category", "")).strip() or "Other", {"count": 0, "credit_total": 0.0, "debit_total": 0.0})
        b["count"] += 1
        b["debit_total" if _is_debit(t) else "credit_total"] += abs(_parse_amount(t.get("amount")))
    for b in by_category.values():
        b["credit_total"], b["debit_total"] = _money(b["credit_total"]), _money(b["debit_total"])
    return {
        "count": len(matched),
        "credit_count": sum(1 for _, t in matched if not _is_debit(t)),
        "debit_count": sum(1 for _, t in matched if _is_debit(t)),
        "credit_total": _money(credit),
        "debit_total": _money(debit),
        "net": _money(credit - debit),
        "by_category": by_category,
        "rows": [
            {
                "#": i,
                "date": t.get("date", ""),
                "description": re.sub(r"\s+", " ", str(t.get("description", ""))).strip(),
                "amount": t.get("amount", ""),
                "type": t.get("type", ""),
                "category": t.get("category", ""),
            }
            for i, t in matched[:QUERY_MAX_ROWS]
        ],
        "rows_truncated": len(matched) > QUERY_MAX_ROWS,
    }


def _numbered_csv(transactions: list[dict]) -> str:
    rows = [{**t, "description": re.sub(r"\s+", " ", str(t.get("description", ""))).strip()} for t in transactions]
    lines = transactions_to_csv(rows).splitlines()
    return "\n".join(["#," + lines[0]] + [f"{i},{line}" for i, line in enumerate(lines[1:], start=1)])


def get_reply(job_data: dict[str, Any], message: str) -> str:
    """
    Answer `message` about the job. job_data: {"transactions": [...], "currency": "..."}.
    """
    transactions = [t for t in (job_data.get("transactions") or []) if isinstance(t, dict)]
    if not transactions:
        return "There are no transactions in this statement to answer from."

    def query_transactions(
        category: str = "",
        category_contains: str = "",
        description_contains: str = "",
        date_contains: str = "",
        type: str = "",
    ) -> dict:
        """Find statement rows and get their exact count and totals. All filters are optional,
        case-insensitive and combined with AND; leave a filter empty to ignore it.

        Args:
            category: Exact category name as shown in the summary table, e.g. "Raast P2P - Sent".
            category_contains: Part of a category name, e.g. "wajid ali" matches "To: WAJID ALI" and "From: WAJID ALI".
            description_contains: Text that must appear in the description, e.g. a name, merchant or "ATM".
            date_contains: Text that must appear in the date as written in the statement, e.g. "Jul 2025" or "2025-07".
            type: "credit" (money in) or "debit" (money out).

        Returns:
            count, credit_count, debit_count, credit_total, debit_total, net (credit minus debit),
            by_category (count and totals per category among the matches), and the matching rows
            (up to 200) with their row numbers (#).
        """
        return query_rows(transactions, category, category_contains, description_contains, date_contains, type)

    csv_text = _numbered_csv(transactions)
    truncated_note = ""
    if len(csv_text) > MAX_CSV_CHARS:
        csv_text = csv_text[:MAX_CSV_CHARS]
        truncated_note = "\n(The listing above is cut short; use query_transactions for rows not shown.)"

    currency = job_data.get("currency") or "unknown"
    totals = official_totals(transactions)
    user_content = (
        f"Statement currency: {currency}\n\n"
        f"OFFICIAL TOTALS (exactly what the summary table shows; summary_total is money in for Income and "
        f"for categories that only have credits, money out for every other category):\n{totals}\n\n"
        f"ALL TRANSACTIONS ({len(transactions)} rows, # = position in the results table):\n{csv_text}{truncated_note}\n\n"
        f"User question: {message}"
    )
    # Keep a reference: a temporary client can be closed mid-call while tool calls are running.
    client = _get_client()
    response = client.models.generate_content(
        model=CHAT_MODEL,
        contents=user_content,
        config=GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0,
            tools=[query_transactions],
            automatic_function_calling=AutomaticFunctionCallingConfig(maximum_remote_calls=MAX_TOOL_CALLS),
        ),
    )
    return (response.text or "").strip()
