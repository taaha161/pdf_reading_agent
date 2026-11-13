"""Turn list of transaction dicts into CSV string."""
import csv
import io
import re
from typing import Any

FIELDS = ["date", "description", "amount", "type", "category"]
_NUMBER_RE = re.compile(r"^-?\d+(\.\d+)?$")

TOTALS_HEADER = ("Category", "Transactions", "Money in", "Money out", "Net")
ALL_CATEGORIES = "All categories"
NO_CATEGORY = "(no category)"


def amount_value(raw: Any) -> float | str:
    """Real number when the amount parses (so a spreadsheet can sum it), else the original text."""
    text = str(raw or "").replace(",", "").strip()
    return float(text) if _NUMBER_RE.match(text) else str(raw or "")


def export_totals(transactions: list[dict[str, Any]]) -> tuple[int, float, float]:
    """(row count, credit total, debit total) over numeric amounts, matching the spreadsheet formulas."""
    credit = debit = 0.0
    for t in transactions:
        value = amount_value(t.get("amount"))
        if isinstance(value, float):
            kind = str(t.get("type") or "").strip().lower()
            if kind == "credit":
                credit += value
            elif kind == "debit":
                debit += value
    return len(transactions), round(credit, 2), round(debit, 2)


def category_totals(transactions: list[dict[str, Any]]) -> list[tuple[str, int, float, float]]:
    """[(category, count, money in, money out)], biggest (in + out) first.

    Categories are grouped case-insensitively, like Excel's "=" comparison, so the cached
    values match what the spreadsheet formulas compute. A blank category is NO_CATEGORY.
    """
    groups: dict[str, list[dict[str, Any]]] = {}
    names: dict[str, str] = {}
    for t in transactions:
        raw = str(t.get("category") or "")
        key = raw.casefold()
        names.setdefault(key, raw or NO_CATEGORY)
        groups.setdefault(key, []).append(t)
    rows = [(names[k], *export_totals(g)) for k, g in groups.items()]
    return sorted(rows, key=lambda r: (-(r[2] + r[3]), r[0].casefold()))


def export_fields(include_categories: bool = True) -> list[str]:
    """Columns for an export; the uncategorized variant drops the category column."""
    return FIELDS if include_categories else [f for f in FIELDS if f != "category"]


def transactions_to_csv(
    transactions: list[dict[str, Any]], include_categories: bool = True, include_totals: bool = False
) -> str:
    """Return CSV string with columns: date, description, amount, type[, category].

    include_totals appends a blank line and a totals table: one row per category (count, money in,
    money out, net) and an "All categories" row. Off by default: accounting imports expect rows only.
    """
    fields = export_fields(include_categories)
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for row in transactions:
        writer.writerow({f: row.get(f) or "" for f in fields})
    if include_totals and transactions:
        table = csv.writer(out)
        table.writerow([])
        table.writerow(TOTALS_HEADER)
        groups = category_totals(transactions) if "category" in fields else []
        count, credit, debit = export_totals(transactions)
        for name, n, money_in, money_out in groups + [(ALL_CATEGORIES, count, credit, debit)]:
            table.writerow([name, n, f"{money_in:.2f}", f"{money_out:.2f}", f"{money_in - money_out:.2f}"])
    return out.getvalue()


def summary_to_csv(summary: list[tuple[str, float]]) -> str:
    """Return CSV string with columns: category, total (two decimals)."""
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["category", "total"])
    for category, total in summary:
        writer.writerow([category, f"{total:.2f}"])
    return out.getvalue()
