"""Category summary shared by the API responses, exports and chat (one definition of the numbers the UI shows)."""


def _parse_amount(amount_str: str) -> float:
    """Parse amount string (may contain commas or leading minus) to float. Returns magnitude."""
    raw = str(amount_str or "0").replace(",", "").strip()
    try:
        return float(raw) if raw else 0.0
    except (ValueError, TypeError):
        return 0.0


def _summary_by_category(transactions: list[dict]) -> list[tuple[str, float]]:
    """Group by category. Income, and any category that has only credits (e.g. "Cash Deposits",
    "From: <name>"), sums credits (money in). Every other category sums debits (money out)."""
    debits: dict[str, float] = {}
    credits: dict[str, float] = {}
    has_debit: set[str] = set()
    for t in transactions:
        magnitude = abs(_parse_amount(t.get("amount")))
        cat = str(t.get("category", "")).strip() or "Other"
        if str(t.get("type", "")).lower() == "debit":
            has_debit.add(cat)
            debits[cat] = debits.get(cat, 0) + magnitude
        else:
            credits[cat] = credits.get(cat, 0) + magnitude
    totals = {
        cat: credits.get(cat, 0.0) if cat == "Income" or cat not in has_debit else debits[cat]
        for cat in debits.keys() | credits.keys()
    }
    return sorted(totals.items(), key=lambda x: -x[1])
