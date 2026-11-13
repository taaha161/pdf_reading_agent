"""Turn list of transaction dicts into CSV string."""
import csv
import io
import re
from typing import Any

FIELDS = ["date", "description", "amount", "type", "category"]
_NUMBER_RE = re.compile(r"^-?\d+(\.\d+)?$")

TOTAL_LABELS = ("Transactions", "Total money in (credits)", "Total money out (debits)", "Net (in - out)")


def amount_value(raw: Any) -> float | str:
    """Real number when the amount parses (so a spreadsheet can sum it), else the original text."""
    text = str(raw or "").replace(",", "").strip()
    return float(text) if _NUMBER_RE.match(text) else str(raw or "")


def export_totals(transactions: list[dict[str, Any]]) -> tuple[int, float, float]:
    """(row count, credit total, debit total) over numeric amounts, matching the spreadsheet SUMIFS."""
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


def export_fields(include_categories: bool = True) -> list[str]:
    """Columns for an export; the uncategorized variant drops the category column."""
    return FIELDS if include_categories else [f for f in FIELDS if f != "category"]


def transactions_to_csv(
    transactions: list[dict[str, Any]], include_categories: bool = True, include_totals: bool = False
) -> str:
    """Return CSV string with columns: date, description, amount, type[, category].

    include_totals appends a blank line and count / money in / money out / net rows (label in the
    description column, value in the amount column). Off by default: accounting imports expect rows only.
    """
    fields = export_fields(include_categories)
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for row in transactions:
        writer.writerow({f: row.get(f) or "" for f in fields})
    if include_totals and transactions:
        count, credit, debit = export_totals(transactions)
        values = (str(count), f"{credit:.2f}", f"{debit:.2f}", f"{credit - debit:.2f}")
        writer.writerow({})
        for label, value in zip(TOTAL_LABELS, values):
            writer.writerow({"description": label, "amount": value})
    return out.getvalue()


def summary_to_csv(summary: list[tuple[str, float]]) -> str:
    """Return CSV string with columns: category, total (two decimals)."""
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["category", "total"])
    for category, total in summary:
        writer.writerow([category, f"{total:.2f}"])
    return out.getvalue()
