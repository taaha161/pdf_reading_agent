"""Running balance for each transaction, from the balances the statement prints.

Many statements print a balance on only some rows (often the last row of each day). We keep
every printed balance and fill the gaps by adding credits and subtracting debits from the
nearest printed one, so every row gets a balance.

Before filling, the printed balances decide two things the rows alone can't tell us:
- order: oldest first (usual) or newest first,
- sign: credits raise the balance (bank accounts) or lower it (credit cards, where the
  balance is what you owe).
If two or more printed balances exist and no reading explains them, we don't guess: only the
printed balances are kept.
"""
import re
from typing import Any

_TOLERANCE = 0.01
# (newest_first, sign) readings, most common first so ties go to the usual layout.
_READINGS = [(False, 1), (False, -1), (True, 1), (True, -1)]


def parse_money(raw: Any) -> float | None:
    """Number from a printed amount/balance: '6,103.27 Cr' -> 6103.27, '1,200.00 DR' -> -1200.0,
    '(50.00)' -> -50.0, '-$12.5' -> -12.5. None when there's no number."""
    text = str(raw or "").strip()
    if not text:
        return None
    negative = False
    upper = text.upper()
    if re.search(r"\b(DR|OD)\b\.?$", upper) or upper.endswith(("DR", "OD")):
        negative = True
    if text.startswith("(") and text.endswith(")"):
        negative = True
    if re.match(r"^\s*[-−]", text) or re.search(r"[-−]\s*$", text):
        negative = True
    digits = re.sub(r"[^0-9.]", "", text.replace(",", ""))
    if not digits or digits.count(".") > 1 or digits == ".":
        return None
    value = float(digits)
    return -value if negative else value


def _net(t: dict[str, Any]) -> float:
    """Signed effect of a row on a bank-account balance: +credit, -debit (0 if unreadable)."""
    value = parse_money(t.get("amount"))
    if value is None:
        return 0.0
    value = abs(value)
    return value if str(t.get("type") or "").strip().lower() == "credit" else -value


def _fill(nets: list[float], stated: dict[int, float], sign: int) -> list[float]:
    """Balances in oldest-first order: printed ones kept, others carried from the nearest printed
    balance (forward from the previous one, or backward before the first one)."""
    n = len(nets)
    first = min(stated)
    out = [0.0] * n
    out[first] = stated[first]
    for i in range(first - 1, -1, -1):  # before the first printed balance: undo row i+1
        out[i] = out[i + 1] - sign * nets[i + 1]
    for i in range(first + 1, n):
        out[i] = stated[i] if i in stated else out[i - 1] + sign * nets[i]
    return out


def _score(nets: list[float], stated: dict[int, float], sign: int) -> int:
    """How many consecutive pairs of printed balances this reading explains (oldest-first order)."""
    idx = sorted(stated)
    hits = 0
    for a, b in zip(idx, idx[1:]):
        expected = stated[a] + sign * sum(nets[a + 1 : b + 1])
        hits += abs(expected - stated[b]) <= _TOLERANCE
    return hits


def _oriented(
    nets: list[float], stated: dict[int, float], newest_first: bool
) -> tuple[list[float], dict[int, float]]:
    """Nets and printed balances in oldest-first order."""
    if not newest_first:
        return nets, stated
    n = len(nets)
    return nets[::-1], {n - 1 - i: v for i, v in stated.items()}


def _best_reading(nets: list[float], stated: dict[int, float]) -> tuple[tuple[bool, int], int]:
    """((newest_first, sign), score) for the reading that explains the most balance steps.
    Ties go to the reading listed first in _READINGS (the usual layout)."""
    best: tuple[tuple[bool, int], int] | None = None
    for newest_first, sign in _READINGS:
        ns, st = _oriented(nets, stated, newest_first)
        score = _score(ns, st, sign)
        if best is None or score > best[1]:
            best = ((newest_first, sign), score)
    assert best is not None
    return best


def fill_running_balances(transactions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Set each row's "balance" to a 2-decimal string (blank when it can't be worked out), and
    "balance_printed" to whether that balance was printed on the statement (vs worked out).

    Rows come in statement order with the printed balance (if any) in "balance".
    Returns the same list, updated in place.
    """
    stated_raw = {i: parse_money(t.get("balance")) for i, t in enumerate(transactions)}
    stated = {i: v for i, v in stated_raw.items() if v is not None}
    for i, t in enumerate(transactions):
        t["balance_printed"] = i in stated
    if not stated:
        for t in transactions:
            t["balance"] = ""
        return transactions

    nets = [_net(t) for t in transactions]
    best = None
    if len(stated) >= 2:
        reading, top = _best_reading(nets, stated)
        if top > 0:
            best = reading
    else:
        best = (False, 1)  # one printed balance: assume the usual layout

    if best is None:  # printed balances don't add up under any reading: keep only those
        for i, t in enumerate(transactions):
            t["balance"] = f"{stated[i]:.2f}" if i in stated else ""
        return transactions

    newest_first, sign = best
    ns, st = _oriented(nets, stated, newest_first)
    filled = _fill(ns, st, sign)
    if newest_first:
        filled = filled[::-1]
    for t, value in zip(transactions, filled):
        t["balance"] = f"{round(value, 2) + 0.0:.2f}"
    return transactions


def printed_balances(transactions: list[dict[str, Any]]) -> dict[int, float] | None:
    """{row index: balance} for the balances printed on the statement, or None for rows saved
    before "balance_printed" existed (their filled-in balances can't be told apart from printed)."""
    if not any("balance_printed" in t for t in transactions):
        return None
    out: dict[int, float] = {}
    for i, t in enumerate(transactions):
        value = parse_money(t.get("balance")) if t.get("balance_printed") else None
        if value is not None:
            out[i] = value
    return out


def balance_breaks(
    transactions: list[dict[str, Any]], stated: dict[int, float]
) -> tuple[tuple[bool, int], list[dict[str, Any]]]:
    """((newest_first, sign), breaks): every step between two consecutive printed balances that
    the rows in between don't explain, under the reading that explains the most steps.

    Each break is {"from_row", "to_row", "rows", "gap"}: the two rows carrying the printed
    balances (statement order), the rows whose amounts make up that step (statement order), and
    printed minus expected balance. stated maps row index -> printed balance (statement order).
    """
    nets = [_net(t) for t in transactions]
    n = len(transactions)
    if len(stated) < 2:
        return (False, 1), []
    (newest_first, sign), _ = _best_reading(nets, stated)
    ns, st = _oriented(nets, stated, newest_first)

    def to_statement(k: int) -> int:
        return n - 1 - k if newest_first else k

    breaks = []
    idx = sorted(st)
    for a, b in zip(idx, idx[1:]):
        gap = st[b] - (st[a] + sign * sum(ns[a + 1 : b + 1]))
        if abs(gap) > _TOLERANCE:
            rows = sorted(to_statement(k) for k in range(a + 1, b + 1))
            breaks.append({
                "from_row": min(to_statement(a), to_statement(b)),
                "to_row": max(to_statement(a), to_statement(b)),
                "rows": rows,
                "gap": round(gap, 2) + 0.0,
            })
    return (newest_first, sign), breaks


def opening_closing(transactions: list[dict[str, Any]]) -> tuple[bool, float, float] | None:
    """(newest_first, opening balance, closing balance) for a whole statement, else None.

    Works from the rows' balances (as filled by fill_running_balances): the opening balance is the
    oldest row's balance with that row undone, the closing balance is the newest row's balance.
    Only when every row has a balance and one reading explains every step between them, so a
    filtered subset of rows, edited amounts or unreliable balances get None instead of a wrong figure.
    """
    n = len(transactions)
    balances = [parse_money(t.get("balance")) for t in transactions]
    if n == 0 or any(b is None for b in balances):
        return None
    nets = [_net(t) for t in transactions]
    readings = _READINGS if n >= 2 else [(False, 1)]  # one row: assume the usual layout
    for newest_first, sign in readings:
        ns = nets[::-1] if newest_first else nets
        bs = balances[::-1] if newest_first else balances
        if _score(ns, dict(enumerate(bs)), sign) == n - 1:
            opening = round(bs[0] - sign * ns[0], 2) + 0.0
            return newest_first, opening, round(bs[-1], 2) + 0.0
    return None
