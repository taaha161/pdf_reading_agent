"""Rewrite printed amounts into one plain format: no thousands separators, "." for decimals.

Statements print numbers in two styles:
- "1,500,000.00" (comma groups, dot decimal), used in the US, UK, Pakistan...
- "1.500.000,00" (dot groups, comma decimal), used in Indonesia and much of Europe.
Everything downstream (totals, balances, exports, the results table) reads "." as the decimal
point, so "1.500.000" would become 1.5 and "150.000" would become 150.

The style is decided once per statement from the numbers that can only be read one way
(e.g. "1.500.000", "12,50", "1,234.56"); values like "150.000" follow that decision. When no
number settles it, currencies without minor units (IDR, JPY...) read "150.000" as 150000.
"""
import re
from typing import Any

# ISO 4217 currencies with no minor unit, or whose statements print whole units only.
_WHOLE_UNIT_CURRENCIES = {
    "IDR", "JPY", "KRW", "VND", "CLP", "PYG", "ISK", "UGX", "RWF", "XAF", "XOF", "KMF",
    "GNF", "DJF", "VUV", "BIF", "XPF", "MGA", "UZS", "LAK", "MMK",
}
_NUMBER = re.compile(r"\d[\d.,\s]*\d|\d")

COMMA_GROUPS = "comma_groups"  # 1,500,000.00
DOT_GROUPS = "dot_groups"  # 1.500.000,00


def _vote(token: str) -> str | None:
    """The style a number can only be read in, or None when it reads either way."""
    token = token.replace(" ", "")
    dots, commas = token.count("."), token.count(",")
    if dots and commas:
        return DOT_GROUPS if token.rfind(",") > token.rfind(".") else COMMA_GROUPS
    if dots > 1:
        return DOT_GROUPS
    if commas > 1:
        return COMMA_GROUPS
    if dots == 1 and not re.search(r"\.\d{3}$", token):
        return COMMA_GROUPS  # "12.5", "12.50": a decimal point
    if commas == 1 and not re.search(r",\d{3}$", token):
        return DOT_GROUPS  # "12,50": a decimal comma
    return None


def detect_style(values: list[Any], currency: str | None = None) -> str:
    votes = {COMMA_GROUPS: 0, DOT_GROUPS: 0}
    for value in values:
        for token in _NUMBER.findall(str(value or "")):
            style = _vote(token)
            if style:
                votes[style] += 1
    if votes[DOT_GROUPS] != votes[COMMA_GROUPS]:
        return DOT_GROUPS if votes[DOT_GROUPS] > votes[COMMA_GROUPS] else COMMA_GROUPS
    if (currency or "").strip().upper() in _WHOLE_UNIT_CURRENCIES:
        return DOT_GROUPS
    return COMMA_GROUPS


def _plain(token: str, style: str) -> str:
    token = token.replace(" ", "")
    group, decimal = (".", ",") if style == DOT_GROUPS else (",", ".")
    return token.replace(group, "").replace(decimal, ".")


def normalize_number(value: Any, style: str) -> str:
    """'1.500.000,00 Cr' -> '1500000.00 Cr' (DOT_GROUPS); markers, signs and brackets are kept."""
    text = str(value or "")
    return _NUMBER.sub(lambda m: _plain(m.group(0), style), text, count=1)


def normalize_amounts(
    transactions: list[dict[str, Any]], currency: str | None = None
) -> list[dict[str, Any]]:
    """Rewrite each row's "amount" and "balance" in place in the plain format."""
    fields = ("amount", "balance")
    style = detect_style([t.get(f) for t in transactions for f in fields], currency)
    for t in transactions:
        for f in fields:
            if str(t.get(f) or "").strip():
                t[f] = normalize_number(t[f], style)
    return transactions
