"""Read a statement's summary box and identity (bank, account, period) with one small Gemini call.

The transaction prompt deliberately skips summary tables, so the printed totals are read here,
separately, from the start and end of the statement (where summary boxes are printed). The
result feeds reconciliation (printed totals vs extracted rows) and account continuity
(which saved statements belong to the same account, and in what order).

Only the last 4 digits of an account number are ever kept.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import date
from typing import Any

from google.genai.types import GenerateContentConfig, ThinkingConfig, ThinkingLevel

from services.balances import parse_money
from services.number_format import detect_style, normalize_number

logger = logging.getLogger("statement_meta")

META_MODEL = "gemini-3.1-flash-lite-preview"
# Summary boxes sit on the first page (most banks) or the last (some cards and EU banks).
HEAD_CHARS = 8000
TAIL_CHARS = 8000
ACCOUNT_TYPES = ("checking", "savings", "credit_card", "other")
AMOUNT_FIELDS = ("opening_balance", "closing_balance", "total_credits", "total_debits")

SYSTEM = (
    "You read the summary of a bank or credit card statement. The input is MARKDOWN from the start "
    "and the end of one statement. Reply with ONE JSON object and nothing else, with these keys:\n"
    '"bank_name": the bank or card issuer, e.g. "Chase" ("" if not shown).\n'
    '"account_last4": the LAST 4 DIGITS of the account or card number only, never more ("" if not shown).\n'
    '"account_type": one of "checking", "savings", "credit_card", "other".\n'
    '"period_start", "period_end": the statement period as YYYY-MM-DD ("" if not shown).\n'
    '"opening_balance": the opening / beginning / previous balance.\n'
    '"closing_balance": the closing / ending / new balance.\n'
    '"total_credits": the printed total of money in. For a bank account: deposits and other credits. '
    "For a credit card: payments and credits.\n"
    '"total_debits": the printed total of money out. For a bank account: withdrawals, checks, fees and '
    "other debits added together. For a credit card: purchases, cash advances, fees and interest added together.\n"
    '"account_count": how many separate accounts this statement lists transactions for (usually 1).\n'
    "Copy every amount exactly as printed, with its separators and any Cr/Dr marker or minus sign. "
    'Use "" for any amount the statement does not print. Never calculate a total the statement does not print, '
    "except adding the printed parts of total_debits for a card as described."
)


def _excerpt(raw_text: str) -> str:
    text = raw_text.strip()
    if len(text) <= HEAD_CHARS + TAIL_CHARS:
        return text
    return text[:HEAD_CHARS] + "\n\n[...]\n\n" + text[-TAIL_CHARS:]


def _iso_date(value: Any) -> str | None:
    text = str(value or "").strip()[:10]
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError:
        return None


def _last4(value: Any) -> str | None:
    digits = re.findall(r"\d", str(value or ""))
    return "".join(digits[-4:]) if len(digits) >= 4 else None


def normalize_meta(raw: dict[str, Any], currency: str | None) -> dict[str, Any]:
    """Model output -> stored shape: amounts as floats (None when not printed), ISO dates,
    last 4 account digits at most, a known account type."""
    style = detect_style([raw.get(f) for f in AMOUNT_FIELDS], currency)
    meta: dict[str, Any] = {}
    for field in AMOUNT_FIELDS:
        text = str(raw.get(field) or "").strip()
        meta[field] = parse_money(normalize_number(text, style)) if text else None
    account_type = str(raw.get("account_type") or "").strip().lower()
    meta["account_type"] = account_type if account_type in ACCOUNT_TYPES else "other"
    meta["bank_name"] = str(raw.get("bank_name") or "").strip()[:80] or None
    meta["account_last4"] = _last4(raw.get("account_last4"))
    meta["period_start"] = _iso_date(raw.get("period_start"))
    meta["period_end"] = _iso_date(raw.get("period_end"))
    try:
        meta["account_count"] = max(1, int(raw.get("account_count") or 1))
    except (TypeError, ValueError):
        meta["account_count"] = 1
    # Totals are sizes; the reconciliation decides which way they move the balance.
    for field in ("total_credits", "total_debits"):
        if meta[field] is not None:
            meta[field] = abs(meta[field])
    if meta["period_start"] and meta["period_end"] and meta["period_start"] > meta["period_end"]:
        meta["period_start"], meta["period_end"] = meta["period_end"], meta["period_start"]
    return meta


def _parse_object(text: str) -> dict[str, Any] | None:
    cleaned = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    match = re.search(r"\{[\s\S]*\}", cleaned)
    if not match:
        return None
    try:
        value = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def extract_statement_meta(raw_text: str, client=None) -> dict[str, Any] | None:
    """The statement's raw (un-normalized) summary fields, or None when it can't be read.
    Never raises: a scan must not fail because its summary couldn't be read."""
    if not raw_text or not raw_text.strip():
        return None
    try:
        if client is None:
            from services.statement_agent import _get_client

            client = _get_client()
        response = client.models.generate_content(
            model=META_MODEL,
            contents=_excerpt(raw_text),
            config=GenerateContentConfig(
                system_instruction=SYSTEM,
                temperature=0,
                max_output_tokens=2048,
                thinking_config=ThinkingConfig(thinking_level=ThinkingLevel.MINIMAL),
            ),
        )
        return _parse_object(response.text or "")
    except Exception as e:  # noqa: BLE001
        logger.warning("extract_statement_meta failed: %s", e)
        return None
