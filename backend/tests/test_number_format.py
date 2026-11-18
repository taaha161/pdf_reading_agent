from services.balances import fill_running_balances
from services.number_format import COMMA_GROUPS, DOT_GROUPS, detect_style, normalize_amounts, normalize_number


def _rows(*pairs):
    return [{"amount": a, "balance": b, "type": "debit"} for a, b in pairs]


def test_indonesian_dot_grouping():
    rows = normalize_amounts(_rows(("150.000", "1.350.000"), ("2.500.000", "")), "IDR")
    assert [r["amount"] for r in rows] == ["150000", "2500000"]
    assert rows[0]["balance"] == "1350000"


def test_dot_groups_with_decimal_comma():
    rows = normalize_amounts(_rows(("1.500.000,00", "6.103,27 Cr")))
    assert rows[0]["amount"] == "1500000.00"
    assert rows[0]["balance"] == "6103.27 Cr"


def test_ambiguous_three_digit_group_uses_currency():
    assert detect_style(["150.000"], "IDR") == DOT_GROUPS
    assert detect_style(["150.000"], "USD") == COMMA_GROUPS


def test_ambiguous_value_follows_statement_style():
    rows = normalize_amounts(_rows(("150.000", ""), ("1.200.000", "")), "USD")
    assert rows[0]["amount"] == "150000"


def test_us_format_unchanged_in_value():
    rows = normalize_amounts(_rows(("1,234.56", "(1,200.00)"), ("50.00", "")), "USD")
    assert rows[0]["amount"] == "1234.56"
    assert rows[0]["balance"] == "(1200.00)"
    assert rows[1]["amount"] == "50.00"


def test_markers_and_signs_kept():
    assert normalize_number("-1.200.000 DR", DOT_GROUPS) == "-1200000 DR"
    assert normalize_number("Rp 25.000", DOT_GROUPS) == "Rp 25000"


def test_running_balance_works_after_normalizing():
    rows = [
        {"amount": "500.000", "type": "credit", "balance": "1.500.000"},
        {"amount": "200.000", "type": "debit", "balance": ""},
    ]
    fill_running_balances(normalize_amounts(rows, "IDR"))
    assert [r["balance"] for r in rows] == ["1500000.00", "1300000.00"]
