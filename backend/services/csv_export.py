"""Turn list of transaction dicts into CSV string."""
import csv
import io
import re
from typing import Any

from services.balances import opening_closing

# Stored/internal row shape (chat context, trial CSV round-trip).
FIELDS = ["date", "description", "amount", "type", "category"]
# Downloaded files are laid out like a statement: separate Debit and Credit columns, then Balance.
DEBIT, CREDIT, BALANCE = "debit", "credit", "balance"
GROUP_FIELD = "group"
_NUMBER_RE = re.compile(r"^-?\d+(\.\d+)?$")

TOTALS_HEADER = ("Category", "Transactions", "Money in", "Money out", "Net")
GROUP_TOTALS_HEADER = ("Sub-category", "Transactions", "Money in", "Money out", "Net")
ALL_CATEGORIES = "All categories"
NO_CATEGORY = "(no category)"
NET_TOTAL = "Net total"
NO_GROUP = "(no sub-category)"
OPENING_BALANCE = "Opening balance"
CLOSING_BALANCE = "Closing balance"
# CSV header labels that differ from the field name (users know groups as sub-categories).
_HEADER_LABELS = {GROUP_FIELD: "sub-category"}


def amount_value(raw: Any) -> float | str:
    """Real number when the amount parses (so a spreadsheet can sum it), else the original text."""
    text = str(raw or "").replace(",", "").strip()
    return float(text) if _NUMBER_RE.match(text) else str(raw or "")


def money_value(raw: Any) -> float | str:
    """Like amount_value but without the sign: Debit/Credit columns hold sizes, the column says
    which way the money went."""
    value = amount_value(raw)
    return abs(value) if isinstance(value, float) else value


def has_balances(transactions: list[dict[str, Any]]) -> bool:
    """True when any row carries a balance (statements without balances get no Balance column)."""
    return any(str(t.get(BALANCE) or "").strip() for t in transactions)


def statement_row(t: dict[str, Any]) -> dict[str, Any]:
    """A stored row with its amount moved into the Debit or Credit column (the other left blank)."""
    kind = str(t.get("type") or "").strip().lower()
    amount = money_value(t.get("amount"))
    row = {**t, DEBIT: "", CREDIT: ""}
    if kind == "credit":
        row[CREDIT] = amount
    elif kind == "debit":
        row[DEBIT] = amount
    else:  # unknown direction: keep the printed amount where it can be seen
        row[DEBIT] = amount
    row[BALANCE] = amount_value(t.get(BALANCE)) if str(t.get(BALANCE) or "").strip() else ""
    return row


def with_balance_rows(rows: list[dict[str, Any]], transactions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Download rows (statement_row shape) with an "Opening balance" row before the oldest transaction
    and a "Closing balance" row after the newest, like a printed statement. Only the Balance cell is
    filled (no Debit/Credit), dated like the transaction next to it. Rows are returned unchanged when
    the balances don't describe a whole statement (see opening_closing)."""
    found = opening_closing(transactions)
    if not found:
        return rows
    newest_first, opening, closing = found
    oldest, newest = (transactions[-1], transactions[0]) if newest_first else (transactions[0], transactions[-1])

    def row(label: str, balance: float, t: dict[str, Any]) -> dict[str, Any]:
        return {"date": t.get("date") or "", "description": label, DEBIT: "", CREDIT: "", BALANCE: balance}

    first, last = row(OPENING_BALANCE, opening, oldest), row(CLOSING_BALANCE, closing, newest)
    if newest_first:
        first, last = row(CLOSING_BALANCE, closing, newest), row(OPENING_BALANCE, opening, oldest)
    return [first, *rows, last]


def export_totals(transactions: list[dict[str, Any]]) -> tuple[int, float, float]:
    """(row count, credit total, debit total) over numeric amounts, matching the spreadsheet formulas."""
    credit = debit = 0.0
    for t in transactions:
        value = money_value(t.get("amount"))
        if isinstance(value, float):
            kind = str(t.get("type") or "").strip().lower()
            if kind == "credit":
                credit += value
            else:  # debit, or unknown (shown in the Debit column, see statement_row)
                debit += value
    return len(transactions), round(credit, 2), round(debit, 2)


def totals_by(
    transactions: list[dict[str, Any]], field: str = "category", blank: str = NO_CATEGORY
) -> list[tuple[str, int, float, float]]:
    """[(value of `field`, count, money in, money out)], biggest (in + out) first.

    Values are grouped case-insensitively, like Excel's "=" comparison, so the cached
    values match what the spreadsheet formulas compute. A blank value is `blank`.
    """
    groups: dict[str, list[dict[str, Any]]] = {}
    names: dict[str, str] = {}
    for t in transactions:
        raw = str(t.get(field) or "")
        key = raw.casefold()
        names.setdefault(key, raw or blank)
        groups.setdefault(key, []).append(t)
    rows = [(names[k], *export_totals(g)) for k, g in groups.items()]
    return sorted(rows, key=lambda r: (-(r[2] + r[3]), r[0].casefold()))


def category_totals(transactions: list[dict[str, Any]]) -> list[tuple[str, int, float, float]]:
    """Per-category totals (see totals_by); a blank category is NO_CATEGORY."""
    return totals_by(transactions, "category", NO_CATEGORY)


def group_totals(transactions: list[dict[str, Any]]) -> list[tuple[str, int, float, float]]:
    """Per-group totals for grouped chat exports (see totals_by); a blank group is NO_GROUP."""
    return totals_by(transactions, GROUP_FIELD, NO_GROUP)


def has_groups(transactions: list[dict[str, Any]]) -> bool:
    """True when any row carries a group label (chat exports grouped by person/merchant)."""
    return any(str(t.get(GROUP_FIELD) or "").strip() for t in transactions)


def export_fields(
    include_categories: bool = True, include_groups: bool = False, include_balance: bool = False
) -> list[str]:
    """Columns of a downloaded file: Date, Description, Debit, Credit[, Balance][, Category][, Sub-category].
    Balance only when the statement had balances; the uncategorized variant drops Category; grouped
    chat exports add the group column (shown as "Sub-category") at the end."""
    fields = ["date", "description", DEBIT, CREDIT]
    if include_balance:
        fields.append(BALANCE)
    if include_categories:
        fields.append("category")
    if include_groups:
        fields.append(GROUP_FIELD)
    return fields


def transactions_to_csv(
    transactions: list[dict[str, Any]],
    include_categories: bool = True,
    include_totals: bool = False,
    ledger: bool = False,
) -> str:
    """Return the CSV a user downloads: date, description, debit, credit[, balance][, category][, sub-category].

    ledger=True instead writes the stored row shape (date, description, amount, type, category), used
    for chat context and the trial CSV round-trip, not for downloads.
    The group column ("Sub-category") is added when any row has a group (grouped chat downloads).
    include_totals appends a blank line and a totals table: one row per category (count, money in,
    money out, net) and an "All categories" row. Grouped rows instead get the category rows without
    "All categories", then a per-sub-category table ending in a "Net total" row. Off by default: accounting imports expect rows only.
    """
    if ledger:
        fields = FIELDS if include_categories else [f for f in FIELDS if f != "category"]
        fields = fields + [GROUP_FIELD] if has_groups(transactions) else fields
        rows = transactions
    else:
        fields = export_fields(include_categories, has_groups(transactions), has_balances(transactions))
        rows = [statement_row(t) for t in transactions]
        if not include_totals:  # totals tables count the data rows, so they keep transactions only
            rows = with_balance_rows(rows, transactions)
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=fields, extrasaction="ignore")
    writer.writerow({f: _HEADER_LABELS.get(f, f) for f in fields})
    for row in rows:
        writer.writerow({f: _cell(row.get(f)) for f in fields})
    if include_totals and transactions:
        table = csv.writer(out)
        table.writerow([])
        table.writerow(TOTALS_HEADER)
        groups = category_totals(transactions) if "category" in fields else []
        count, credit, debit = export_totals(transactions)
        grouped = GROUP_FIELD in fields
        # Grouped files end in "Net total" instead, so the same figure isn't shown twice.
        all_row = [] if grouped and groups else [(ALL_CATEGORIES, count, credit, debit)]
        for name, n, money_in, money_out in groups + all_row:
            table.writerow([name, n, f"{money_in:.2f}", f"{money_out:.2f}", f"{money_in - money_out:.2f}"])
        if grouped:
            table.writerow([])
            table.writerow(GROUP_TOTALS_HEADER)
            for name, n, money_in, money_out in group_totals(transactions) + [(NET_TOTAL, count, credit, debit)]:
                table.writerow([name, n, f"{money_in:.2f}", f"{money_out:.2f}", f"{money_in - money_out:.2f}"])
    return out.getvalue()


def _cell(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.2f}"
    return "" if value is None else str(value)


def summary_to_csv(summary: list[tuple[str, float]]) -> str:
    """Return CSV string with columns: category, total (two decimals)."""
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["category", "total"])
    for category, total in summary:
        writer.writerow([category, f"{total:.2f}"])
    return out.getvalue()
