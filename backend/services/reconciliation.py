"""Does a statement's extracted transactions add up?

Pure functions over the stored row shape, recomputed on every read so user edits are reflected.

Balance chain: between every two balances printed on the statement, the rows in between must
explain the step (previous balance + credits - debits = next balance; reversed for credit cards).
A step that doesn't add up pins the error to those rows, and the size of the gap usually says what
went wrong: a row read with the wrong direction, a row read twice, or a row missed.
"""
from __future__ import annotations

from typing import Any

from services.balances import _TOLERANCE, _net, balance_breaks, opening_closing, parse_money, printed_balances

RECONCILED, MISMATCH, UNVERIFIED = "reconciled", "mismatch", "unverified"
PASS, FAIL, SKIPPED = "pass", "fail", "skipped"
# Long statements can break in many places; the first few are enough to act on.
MAX_HINTS = 20

REASON_NO_BALANCES = "This statement doesn't print running balances, so there's nothing to check the rows against."
REASON_ONE_BALANCE = "This statement prints only one balance, so there's nothing to check the rows against."
REASON_LEGACY = "Scanned before balance checks were added. Scan the statement again to check it."
REASON_NO_ROWS = "No transactions were found."


def _close(a: float, b: float) -> bool:
    return abs(a - b) <= _TOLERANCE + 1e-9


def _money(value: float) -> float:
    return round(value, 2) + 0.0


def _totals(transactions: list[dict[str, Any]]) -> tuple[float, float]:
    """(total credits, total debits) as positive sizes."""
    credits = debits = 0.0
    for t in transactions:
        net = _net(t)
        if net > 0:
            credits += net
        else:
            debits -= net
    return _money(credits), _money(debits)


def _row_key(t: dict[str, Any]) -> tuple:
    return (str(t.get("date") or ""), str(t.get("description") or "").strip().casefold(), _net(t))


def _all_same_duplicate(transactions: list[dict[str, Any]], candidates: list[dict[str, Any]]) -> bool:
    """True when every candidate is a "read twice" match on identical rows (same date, description
    and amount), so it doesn't matter which copy we point at."""
    if not all(c["kind"] == "duplicate_row" for c in candidates):
        return False
    return len({_row_key(transactions[c["row_index"]]) for c in candidates}) == 1


def _hint_for_break(transactions: list[dict[str, Any]], brk: dict[str, Any], sign: int) -> dict[str, Any] | None:
    """The likely cause of one break, or None when more than one row could explain it.

    With gap = printed - expected balance and a row's signed effect net:
    - that row has the wrong direction  -> gap == -2 * sign * net
    - that row was read twice          -> gap == -sign * net
    - otherwise a row is missing whose signed effect is sign * gap.
    """
    gap = brk["gap"]
    candidates = []
    for i in brk["rows"]:
        net = _net(transactions[i])
        if net == 0:
            continue
        if _close(gap, -2 * sign * net):
            candidates.append({"kind": "flipped_type", "row_index": i, "amount": _money(abs(net))})
        elif _close(gap, -sign * net):
            candidates.append({"kind": "duplicate_row", "row_index": i, "amount": _money(abs(net))})
    if len(candidates) == 1:
        return candidates[0]
    if _all_same_duplicate(transactions, candidates):
        return candidates[-1]  # a row read twice: the later copy is the extra one
    if candidates:
        return None
    missing = sign * gap
    return {
        "kind": "missing_row",
        "from_row": brk["from_row"],
        "to_row": brk["to_row"],
        "amount": _money(abs(missing)),
        "direction": "credit" if missing > 0 else "debit",
    }


def _balance_chain(transactions: list[dict[str, Any]], stated: dict[int, float]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """(check, hints) for the printed running balances."""
    (newest_first, sign), breaks = balance_breaks(transactions, stated)
    order = sorted(stated, reverse=newest_first)  # oldest printed balance first
    first, last = order[0], order[-1]
    span = range(min(first, last), max(first, last) + 1)
    # Rows between the oldest and newest printed balance, excluding the oldest one's own row.
    moved = sum(_net(transactions[i]) for i in span if i != first)
    expected = stated[first] + sign * moved
    check = {
        "key": "balance_chain",
        "status": FAIL if breaks else PASS,
        "expected": _money(stated[last]),
        "actual": _money(expected),
        "difference": _money(stated[last] - expected),
        "breaks": len(breaks),
    }
    hints = [h for h in (_hint_for_break(transactions, b, sign) for b in breaks[:MAX_HINTS]) if h]
    return check, hints


def reconcile(transactions: list[dict[str, Any]]) -> dict[str, Any]:
    """Reconciliation result for one statement (see schemas.Reconciliation)."""
    credits, debits = _totals(transactions)
    result: dict[str, Any] = {
        "status": UNVERIFIED,
        "reason": None,
        "opening_balance": None,
        "closing_balance": None,
        "total_credits": credits,
        "total_debits": debits,
        "checks": [],
        "hints": [],
    }
    if not transactions:
        result["reason"] = REASON_NO_ROWS
        return result

    found = opening_closing(transactions)
    if found:
        _, result["opening_balance"], result["closing_balance"] = found

    stated = printed_balances(transactions)
    if stated is None:
        result["reason"] = REASON_LEGACY if any(parse_money(t.get("balance")) is not None for t in transactions) else REASON_NO_BALANCES
        return result
    if len(stated) < 2:
        result["reason"] = REASON_ONE_BALANCE if stated else REASON_NO_BALANCES
        return result

    check, hints = _balance_chain(transactions, stated)
    result["checks"].append(check)
    result["hints"] = hints
    result["status"] = MISMATCH if check["status"] == FAIL else RECONCILED
    return result
