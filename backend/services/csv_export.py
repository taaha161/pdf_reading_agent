"""Turn list of transaction dicts into CSV string."""
import csv
import io
from typing import Any

FIELDS = ["date", "description", "amount", "type", "category"]


def export_fields(include_categories: bool = True) -> list[str]:
    """Columns for an export; the uncategorized variant drops the category column."""
    return FIELDS if include_categories else [f for f in FIELDS if f != "category"]


def transactions_to_csv(transactions: list[dict[str, Any]], include_categories: bool = True) -> str:
    """Return CSV string with columns: date, description, amount, type[, category]."""
    fields = export_fields(include_categories)
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for row in transactions:
        writer.writerow({f: row.get(f) or "" for f in fields})
    return out.getvalue()


def summary_to_csv(summary: list[tuple[str, float]]) -> str:
    """Return CSV string with columns: category, total (two decimals)."""
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["category", "total"])
    for category, total in summary:
        writer.writerow([category, f"{total:.2f}"])
    return out.getvalue()
