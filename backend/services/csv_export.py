"""Turn list of transaction dicts into CSV string."""
import csv
import io
from typing import Any


def transactions_to_csv(transactions: list[dict[str, Any]]) -> str:
    """Return CSV string with columns: date, description, amount, type, category."""
    if not transactions:
        return "date,description,amount,type,category\n"

    out = io.StringIO()
    writer = csv.DictWriter(
        out,
        fieldnames=["date", "description", "amount", "type", "category"],
        extrasaction="ignore",
    )
    writer.writeheader()
    for row in transactions:
        writer.writerow(
            {
                "date": row.get("date", ""),
                "description": row.get("description", ""),
                "amount": row.get("amount", ""),
                "type": row.get("type", ""),
                "category": row.get("category", ""),
            }
        )
    return out.getvalue()
