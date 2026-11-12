"""Category summary: debits for spending categories, credits for Income and credit-only categories."""
from main import _summary_by_category


def tx(category, type_, amount):
    return {"category": category, "type": type_, "amount": str(amount)}


def test_mixed_category_keeps_credits_in_own_row():
    """A refund under POS, or money received under Transfer, must not disappear."""
    summary = dict(_summary_by_category([
        tx("POS", "debit", 100), tx("POS", "credit", 40),
        tx("Transfer", "debit", 10), tx("Transfer", "credit", 768000),
    ]))
    assert summary == {"POS": 100, "POS (money in)": 40, "Transfer": 10, "Transfer (money in)": 768000}


def test_income_with_debit_keeps_debit_in_own_row():
    assert dict(_summary_by_category([tx("Income", "credit", 500), tx("Income", "debit", 20)])) == {
        "Income": 500, "Income (money out)": 20,
    }


def test_no_money_lost():
    rows = [tx("POS", "debit", 7), tx("POS", "credit", 3), tx("Income", "credit", 11),
            tx("Income", "debit", 2), tx("Cash Deposits", "credit", 5), tx("", "debit", 1)]
    assert sum(t for _, t in _summary_by_category(rows)) == 29


def test_single_direction_categories_have_no_extra_row():
    summary = dict(_summary_by_category([tx("Dining", "debit", 9), tx("Income", "credit", 4)]))
    assert summary == {"Dining": 9, "Income": 4}


def test_credit_only_category_shows_money_in_not_zero():
    summary = dict(_summary_by_category([tx("Cash Deposits", "credit", 300), tx("From: ALI", "credit", 50)]))
    assert summary == {"Cash Deposits": 300, "From: ALI": 50}


def test_sorted_by_total_descending():
    assert [c for c, _ in _summary_by_category([tx("A", "debit", 1), tx("B", "credit", 9)])] == ["B", "A"]
