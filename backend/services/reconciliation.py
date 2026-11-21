"""Do a statement's extracted transactions add up?

Pure functions over the stored row shape, recomputed on every read so user edits are reflected.

Balance chain: between every two balances printed on the statement, the rows in between must
explain the step (previous balance + credits - debits = next balance; reversed for credit cards).
A step that doesn't add up pins the error to those rows, and the size of the gap usually says what
went wrong: a row read with the wrong direction, a row read twice, or a row missed.

Printed summary: when the statement's summary box was read (statement_meta), the rows must match
its opening balance, total money in, total money out and closing balance. This also works for
statements that print no running balances.
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
REASON_MULTI_ACCOUNT = "This statement covers more than one account, so its totals can't be checked against the rows."


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


def _balance_chain(
    transactions: list[dict[str, Any]], stated: dict[int, float], sign: int | None
) -> tuple[dict[str, Any], list[dict[str, Any]], int]:
    """(check, hints, sign used) for the printed running balances."""
    (newest_first, sign), breaks = balance_breaks(transactions, stated, sign)
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
    return check, hints, sign


def _summary_sign(meta: dict[str, Any]) -> int | None:
    """+1 when money in raises the balance (bank account), -1 when it lowers it (credit card),
    from the account type or, failing that, from which way the printed summary adds up."""
    kind = meta.get("account_type")
    if kind == "credit_card":
        return -1
    if kind in ("checking", "savings"):
        return 1
    o, c, cr, dr = (meta.get(k) for k in ("opening_balance", "closing_balance", "total_credits", "total_debits"))
    if None in (o, c, cr, dr):
        return None
    if _close(o + cr - dr, c):
        return 1
    if _close(o - cr + dr, c):
        return -1
    return None


def _summary_consistent(meta: dict[str, Any], sign: int) -> bool | None:
    """Does the printed summary add up on its own (opening + in - out = closing)? None when it
    doesn't print all four figures. A summary that doesn't add up was misread, so the rows
    aren't blamed for disagreeing with it."""
    o, c, cr, dr = (meta.get(k) for k in ("opening_balance", "closing_balance", "total_credits", "total_debits"))
    if None in (o, c, cr, dr):
        return None
    return _close(o + sign * (cr - dr), c)


def _compare(key: str, printed: float | None, extracted: float | None, usable: bool) -> dict[str, Any]:
    if printed is None or extracted is None or not usable:
        return {"key": key, "status": SKIPPED, "expected": printed, "actual": extracted, "difference": None}
    diff = _money(printed - extracted)
    return {
        "key": key,
        "status": PASS if _close(printed, extracted) else FAIL,
        "expected": _money(printed),
        "actual": _money(extracted),
        "difference": diff,
    }


def _summary_checks(
    meta: dict[str, Any], sign: int, credits: float, debits: float, derived: tuple[float, float] | None
) -> list[dict[str, Any]]:
    """Printed summary vs extracted rows: opening, money in, money out, closing."""
    usable = _summary_consistent(meta, sign) is not False
    opening = meta.get("opening_balance")
    if opening is not None:
        closing_from_rows = opening + sign * (credits - debits)  # needs no running balances
    else:
        closing_from_rows = derived[1] if derived else None
    return [
        _compare("opening", opening, derived[0] if derived else None, usable),
        _compare("credits", meta.get("total_credits"), credits, usable),
        _compare("debits", meta.get("total_debits"), debits, usable),
        _compare("closing", meta.get("closing_balance"), closing_from_rows, usable),
    ]


def reconcile(transactions: list[dict[str, Any]], meta: dict[str, Any] | None = None) -> dict[str, Any]:
    """Reconciliation result for one statement (see schemas.Reconciliation).

    meta is the statement's printed summary (statement_meta.normalize_meta), when it was read.
    """
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
    if meta and (meta.get("account_count") or 1) > 1:
        result["reason"] = REASON_MULTI_ACCOUNT
        return result

    found = opening_closing(transactions)
    derived = (found[1], found[2]) if found else None
    if derived:
        result["opening_balance"], result["closing_balance"] = derived

    sign = _summary_sign(meta) if meta else None
    stated = printed_balances(transactions)
    if stated is not None and len(stated) >= 2:
        check, hints, sign = _balance_chain(transactions, stated, sign)
        result["checks"].append(check)
        result["hints"] = hints

    if meta:
        summary = _summary_checks(meta, sign or 1, credits, debits, derived)
        if any(c["status"] != SKIPPED for c in summary):
            result["checks"].extend(summary)
            if meta.get("opening_balance") is not None:
                result["opening_balance"] = meta["opening_balance"]
            if meta.get("closing_balance") is not None:
                result["closing_balance"] = meta["closing_balance"]

    statuses = {c["status"] for c in result["checks"]}
    if FAIL in statuses:
        result["status"] = MISMATCH
    elif PASS in statuses:
        result["status"] = RECONCILED
    elif stated is None:
        has_balances = any(parse_money(t.get("balance")) is not None for t in transactions)
        result["reason"] = REASON_LEGACY if has_balances else REASON_NO_BALANCES
    else:
        result["reason"] = REASON_ONE_BALANCE if stated else REASON_NO_BALANCES
    return result
