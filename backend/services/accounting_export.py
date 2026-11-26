"""Import-ready CSV files for QuickBooks Online and Xero bank statement imports.

Both importers want one signed Amount column (money in positive, money out negative) and one date
format for the whole file, with no balance, totals or opening/closing rows (those would import as
transactions). Statements print dates many ways ("01/05/2024", "05 Jan 24", "Jan 5"), and rows keep
the printed text, so dates are rewritten here into one full date format:

- MM/DD/YYYY when the statement's dates are month-first (US style),
- DD/MM/YYYY when they are day-first (UK, AU, NZ, EU...).

The order is decided once per file from dates that can only be read one way (a part above 12), then
from the currency (USD → month-first, most others day-first), the same way number_format decides
separators. A date with no year gets the latest year that doesn't put it in the future. A date that
can't be read is written as printed so the importer flags that row instead of the file failing.

QuickBooks Online "3-column" layout: Date, Description, Amount.
Xero statement import layout: Date, Amount, Payee, Description, Reference.
"""
from __future__ import annotations

import csv
import io
import re
from datetime import date
from typing import Any

from services.csv_export import amount_value

QUICKBOOKS = "quickbooks"
XERO = "xero"
ACCOUNTING_FORMATS = (QUICKBOOKS, XERO)

QUICKBOOKS_HEADER = ("Date", "Description", "Amount")
XERO_HEADER = ("Date", "Amount", "Payee", "Description", "Reference")

MONTH_FIRST, DAY_FIRST = "mdy", "dmy"
# Currencies whose statements print month-first dates. Everything else defaults to day-first.
_MONTH_FIRST_CURRENCIES = {"USD", "PHP"}

_MONTHS = {
    name: i + 1
    for i, names in enumerate(
        [
            ("jan", "january"), ("feb", "february"), ("mar", "march"), ("apr", "april"),
            ("may",), ("jun", "june"), ("jul", "july"), ("aug", "august"),
            ("sep", "sept", "september"), ("oct", "october"), ("nov", "november"), ("dec", "december"),
        ]
    )
    for name in names
}
_ISO = re.compile(r"^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})")
_NUMERIC = re.compile(r"^(\d{1,2})[-/.](\d{1,2})(?:[-/.](\d{2}|\d{4}))?$")
# "5 Jan 2024", "05-Jan-24", "05JAN24", "5 January"
_DAY_MONTH = re.compile(r"^(\d{1,2})(?:st|nd|rd|th)?[\s\-/.]*([a-z]{3,9})\.?[\s\-/.,]*(\d{2}|\d{4})?$")
# "Jan 5, 2024", "January 05 2024", "Jan-05", "Jan 5"
# Some banks print the weekday first ("Mon 05 Jan 2024", "Tue, 01/02/24"); importers reject it.
_WEEKDAY = re.compile(r"^(mon|tue|wed|thu|fri|sat|sun)[a-z]*\.?,?\s+")
_MONTH_DAY = re.compile(r"^([a-z]{3,9})\.?[\s\-/.]*(\d{1,2})(?:st|nd|rd|th)?[\s\-/.,]*(\d{2}|\d{4})?$")


def _year(text: str | None) -> int | None:
    if not text:
        return None
    value = int(text)
    return value + 2000 if value < 100 else value


def _numeric_parts(raw: str) -> tuple[int, int] | None:
    """(first, second) of a numeric day/month date like "05/01/2024", else None."""
    m = _NUMERIC.match(raw.strip())
    return (int(m.group(1)), int(m.group(2))) if m else None


def date_order(dates: list[str], currency: str | None = None) -> str:
    """MONTH_FIRST or DAY_FIRST for a file's numeric dates (see module docstring)."""
    for raw in dates:
        parts = _numeric_parts(_WEEKDAY.sub("", str(raw or "").strip().lower()))
        if not parts:
            continue
        first, second = parts
        if first > 12 >= second:
            return DAY_FIRST
        if second > 12 >= first:
            return MONTH_FIRST
    return MONTH_FIRST if (currency or "USD").strip().upper() in _MONTH_FIRST_CURRENCIES else DAY_FIRST


def parse_date(raw: Any, order: str, today: date | None = None) -> date | None:
    """The calendar date of a printed statement date, or None if it can't be read."""
    text = _WEEKDAY.sub("", re.sub(r"\s+", " ", str(raw or "").strip().lower()))
    if not text:
        return None
    today = today or date.today()
    year = month = day = None
    if m := _ISO.match(text):
        year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
    elif m := _NUMERIC.match(text):
        a, b = int(m.group(1)), int(m.group(2))
        month, day = (a, b) if order == MONTH_FIRST else (b, a)
        year = _year(m.group(3))
    elif (m := _DAY_MONTH.match(text)) and m.group(2) in _MONTHS:
        day, month, year = int(m.group(1)), _MONTHS[m.group(2)], _year(m.group(3))
    elif (m := _MONTH_DAY.match(text)) and m.group(1) in _MONTHS:
        month, day, year = _MONTHS[m.group(1)], int(m.group(2)), _year(m.group(3))
    else:
        return None
    try:
        if year is None:  # no year printed: the latest year that doesn't put the date in the future
            found = date(today.year, month, day)
            return found if found <= today else date(today.year - 1, month, day)
        return date(year, month, day)
    except ValueError:  # 31/02, Feb 29 in a non-leap year...
        return None


def format_date(raw: Any, order: str, today: date | None = None) -> str:
    """The date as MM/DD/YYYY or DD/MM/YYYY (by `order`), or the printed text if unreadable."""
    found = parse_date(raw, order, today)
    if not found:
        return str(raw or "").strip()
    if order == MONTH_FIRST:
        return f"{found.month:02d}/{found.day:02d}/{found.year}"
    return f"{found.day:02d}/{found.month:02d}/{found.year}"


def signed_amount(t: dict[str, Any]) -> str:
    """Money in positive, money out negative, two decimals. Unknown direction keeps the printed sign;
    an amount that isn't a number is written as printed."""
    value = amount_value(t.get("amount"))
    if not isinstance(value, float):
        return str(value).strip()
    kind = str(t.get("type") or "").strip().lower()
    if kind == "credit":
        value = abs(value)
    elif kind == "debit":
        value = -abs(value)
    return f"{value:.2f}"


def _safe(text: Any) -> str:
    """Keep a description starting with = + - @ from running as a formula when opened in Excel."""
    value = str(text or "").strip()
    return "'" + value if value[:1] in ("=", "+", "-", "@", "\t", "\r") else value


def accounting_csv(
    transactions: list[dict[str, Any]],
    target: str,
    currency: str | None = None,
    today: date | None = None,
) -> str:
    """The CSV for `target` (QUICKBOOKS or XERO): transactions only, in statement order."""
    order = date_order([t.get("date") for t in transactions], currency)
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(XERO_HEADER if target == XERO else QUICKBOOKS_HEADER)
    for t in transactions:
        when = format_date(t.get("date"), order, today)
        description = _safe(t.get("description"))
        amount = signed_amount(t)
        if target == XERO:
            writer.writerow([when, amount, description, "", ""])
        else:
            writer.writerow([when, description, amount])
    return out.getvalue()


def accounting_filename(target: str, combined: bool = False) -> str:
    base = "statements-combined" if combined else "statement"
    return f"{base}-{target}.csv"
