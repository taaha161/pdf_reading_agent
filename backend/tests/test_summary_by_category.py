"""Category summary: debits for spending categories, credits for Income and credit-only categories."""
from main import _summary_by_category


def tx(category, type_, amount):
    return {"category": category, "type": type_, "amount": str(amount)}


def test_spending_category_sums_debits_only():
    assert dict(_summary_by_category([tx("Transfer", "debit", 100), tx("Transfer", "credit", 40)])) == {"Transfer": 100}


def test_income_sums_credits_only():
    assert dict(_summary_by_category([tx("Income", "credit", 500), tx("Income", "debit", 20)])) == {"Income": 500}


def test_credit_only_category_shows_money_in_not_zero():
    summary = dict(_summary_by_category([tx("Cash Deposits", "credit", 300), tx("From: ALI", "credit", 50)]))
    assert summary == {"Cash Deposits": 300, "From: ALI": 50}


def test_sorted_by_total_descending():
    assert [c for c, _ in _summary_by_category([tx("A", "debit", 1), tx("B", "credit", 9)])] == ["B", "A"]
