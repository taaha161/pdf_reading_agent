"""Category summary shared by the API responses, exports and chat (one definition of the numbers the UI shows)."""

# Suffixes for the second row of a category that has both money in and money out
# (e.g. "POS" debits plus a refund). Mirrored in frontend/src/lib/transactionDirection.js.
MONEY_IN_SUFFIX = " (money in)"
MONEY_OUT_SUFFIX = " (money out)"


def _parse_amount(amount_str: str) -> float:
    """Parse amount string (may contain commas or leading minus) to float. Returns magnitude."""
    raw = str(amount_str or "0").replace(",", "").strip()
    try:
        return float(raw) if raw else 0.0
    except (ValueError, TypeError):
        return 0.0


def _summary_by_category(transactions: list[dict]) -> list[tuple[str, float]]:
    """Group by category without dropping any money.

    Each category's main row sums its primary direction: credits for Income and for
    credit-only categories (e.g. "Cash Deposits", "From: <name>"), debits otherwise.
    If a category also has the other direction (a refund under "POS", money received
    under "Transfer"), that total gets its own row: "<category> (money in)" or
    "<category> (money out)".
    """
    debits: dict[str, float] = {}
    credits: dict[str, float] = {}
    for t in transactions:
        magnitude = abs(_parse_amount(t.get("amount")))
        cat = str(t.get("category", "")).strip() or "Other"
        if str(t.get("type", "")).lower() == "debit":
            debits[cat] = debits.get(cat, 0) + magnitude
        else:
            credits[cat] = credits.get(cat, 0) + magnitude

    totals: dict[str, float] = {}
    for cat in debits.keys() | credits.keys():
        credit_primary = cat == "Income" or cat not in debits
        if credit_primary:
            totals[cat] = credits.get(cat, 0.0)
            if cat in debits:
                totals[cat + MONEY_OUT_SUFFIX] = debits[cat]
        else:
            totals[cat] = debits[cat]
            if cat in credits:
                totals[cat + MONEY_IN_SUFFIX] = credits[cat]
    return sorted(totals.items(), key=lambda x: -x[1])
