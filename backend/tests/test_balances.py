"""Tests for running balances filled in from the balances a statement prints."""
from services.balances import fill_running_balances, parse_money


def _rows(spec):
    """spec: (type, amount, printed balance or "")."""
    return [{"type": t, "amount": a, "balance": b} for t, a, b in spec]


def _balances(rows):
    return [r["balance"] for r in fill_running_balances(rows)]


def test_parse_money_markers():
    assert parse_money("6,103.27 Cr") == 6103.27
    assert parse_money("1,200.00 DR") == -1200.0
    assert parse_money("1,200.00Dr") == -1200.0
    assert parse_money("(50.00)") == -50.0
    assert parse_money("-$12.50") == -12.5
    assert parse_money("12.50-") == -12.5
    assert parse_money("− 7.00") == -7.0
    assert parse_money("") is None and parse_money("n/a") is None and parse_money(None) is None


def test_balance_printed_only_at_end_of_day():
    # Westpac-style: several rows per day, balance on the last row of each day; the opening
    # balance row itself is excluded from the transactions.
    rows = _rows([
        ("credit", "264.06", ""),
        ("credit", "22,500.00", "28,867.33 Cr"),
        ("debit", "15,000.00", "13,867.33 Cr"),
        ("debit", "5,000.00", ""),
        ("debit", "491.86", "8,375.47 Cr"),
    ])
    assert _balances(rows) == ["6367.33", "28867.33", "13867.33", "8867.33", "8375.47"]


def test_rows_before_first_printed_balance_are_worked_backwards():
    rows = _rows([("debit", "10", ""), ("debit", "20", ""), ("credit", "5", "75.00")])
    assert _balances(rows) == ["90.00", "70.00", "75.00"]


def test_newest_first_statement():
    # Newest row on top: each balance is the one below it plus this row's effect.
    rows = _rows([("debit", "30", "70.00"), ("credit", "50", ""), ("debit", "20", "50.00")])
    assert _balances(rows) == ["70.00", "100.00", "50.00"]


def test_credit_card_balance_goes_up_with_spending():
    rows = _rows([("debit", "40", "140.00"), ("debit", "10", ""), ("credit", "100", "50.00")])
    assert _balances(rows) == ["140.00", "150.00", "50.00"]


def test_overdrawn_balances():
    rows = _rows([("debit", "100", "-50.00"), ("debit", "25", ""), ("credit", "10", "65.00 DR")])
    assert _balances(rows) == ["-50.00", "-75.00", "-65.00"]


def test_printed_balance_wins_over_arithmetic():
    # A missed row upstream makes the sum disagree once; the printed figure resets the run.
    rows = _rows([("debit", "10", "90.00"), ("debit", "10", "75.00"), ("debit", "5", ""), ("debit", "5", "65.00")])
    assert _balances(rows) == ["90.00", "75.00", "70.00", "65.00"]


def test_inconsistent_printed_balances_are_not_filled():
    rows = _rows([("debit", "10", "500.00"), ("debit", "10", ""), ("debit", "10", "3.00")])
    assert _balances(rows) == ["500.00", "", "3.00"]


def test_no_printed_balances_leaves_blank():
    rows = _rows([("debit", "10", ""), ("credit", "5", "")])
    assert _balances(rows) == ["", ""]


def test_single_printed_balance_fills_both_ways():
    rows = _rows([("debit", "10", ""), ("credit", "5", "100.00"), ("debit", "1.50", "")])
    assert _balances(rows) == ["95.00", "100.00", "98.50"]


def test_page_break_rows_are_dropped_and_keep_their_balance():
    from services.statement_agent import _drop_page_break_rows

    rows = [
        {"description": "EFTPOS United", "amount": "81.32", "type": "debit", "balance": ""},
        {"description": "V6509 Petstock Som", "amount": "0.0", "type": "credit", "balance": "7,579.10 Cr"},
        {"description": "Brought forward", "amount": "", "type": "debit", "balance": "7,579.10 Cr"},
        {"description": "Erville 749", "amount": "16.00", "type": "debit", "balance": "7,563.10 Cr"},
        {"description": "Odd amount", "amount": "n/a", "type": "debit", "balance": ""},
    ]
    kept = _drop_page_break_rows(rows)
    assert [r["description"] for r in kept] == ["EFTPOS United", "Erville 749", "Odd amount"]
    assert kept[0]["balance"] == "7,579.10 Cr"  # anchor kept for the running balance
