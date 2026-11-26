"""QuickBooks Online and Xero import CSVs (services/accounting_export.py, /api/export formats)."""
from datetime import date

from services.accounting_export import (
    DAY_FIRST,
    MONTH_FIRST,
    accounting_csv,
    date_order,
    format_date,
    signed_amount,
)

TODAY = date(2026, 11, 25)
ROWS = [
    {"date": "2024-01-01", "description": "Coffee", "amount": "-4.50", "type": "debit", "category": "Food", "balance": "95.50"},
    {"date": "2024-01-02", "description": "=1+1", "amount": "1,200.00", "type": "credit", "category": None},
]


def test_date_order_from_unambiguous_dates():
    assert date_order(["01/02/2024", "25/02/2024"]) == DAY_FIRST
    assert date_order(["01/02/2024", "02/25/2024"]) == MONTH_FIRST


def test_date_order_falls_back_to_currency():
    assert date_order(["01/02/2024"], "USD") == MONTH_FIRST
    assert date_order(["01/02/2024"], None) == MONTH_FIRST
    assert date_order(["01/02/2024"], "GBP") == DAY_FIRST
    assert date_order(["01/02/2024"], "aud") == DAY_FIRST


def test_format_date_handles_printed_styles():
    cases = {
        "2024-01-05": "01/05/2024",
        "01/05/2024": "01/05/2024",
        "1/5/24": "01/05/2024",
        "Jan 5, 2024": "01/05/2024",
        "January 05 2024": "01/05/2024",
        "05 Jan 2024": "01/05/2024",
        "05-Jan-24": "01/05/2024",
        "05JAN24": "01/05/2024",
        "5th Jan 2024": "01/05/2024",
        "Sept 9 2024": "09/09/2024",
        "Fri 05 Jan 2024": "01/05/2024",
        "Fri, 01/05/2024": "01/05/2024",
    }
    for raw, expected in cases.items():
        assert format_date(raw, MONTH_FIRST, TODAY) == expected, raw
    assert format_date("05/01/2024", DAY_FIRST, TODAY) == "05/01/2024"
    assert format_date("2024-01-05", DAY_FIRST, TODAY) == "05/01/2024"


def test_missing_year_is_latest_year_not_in_future():
    assert format_date("Nov 20", MONTH_FIRST, TODAY) == "11/20/2026"
    assert format_date("Dec 28", MONTH_FIRST, TODAY) == "12/28/2025"
    assert format_date("28/12", DAY_FIRST, TODAY) == "28/12/2025"


def test_unreadable_date_kept_as_printed():
    assert format_date("Pending", MONTH_FIRST, TODAY) == "Pending"
    assert format_date("31/02/2024", DAY_FIRST, TODAY) == "31/02/2024"
    assert format_date("", MONTH_FIRST, TODAY) == ""


def test_signed_amount():
    assert signed_amount({"amount": "4.50", "type": "debit"}) == "-4.50"
    assert signed_amount({"amount": "-4.50", "type": "debit"}) == "-4.50"
    assert signed_amount({"amount": "1,200", "type": "credit"}) == "1200.00"
    assert signed_amount({"amount": "-7", "type": ""}) == "-7.00"
    assert signed_amount({"amount": "n/a", "type": "debit"}) == "n/a"


def test_quickbooks_layout():
    lines = accounting_csv(ROWS, "quickbooks", "USD", TODAY).splitlines()
    assert lines == [
        "Date,Description,Amount",
        "01/01/2024,Coffee,-4.50",
        "01/02/2024,'=1+1,1200.00",
    ]


def test_xero_layout_day_first_for_gbp():
    lines = accounting_csv(ROWS, "xero", "GBP", TODAY).splitlines()
    assert lines == [
        "Date,Amount,Payee,Description,Reference",
        "01/01/2024,-4.50,Coffee,,",
        "02/01/2024,1200.00,'=1+1,,",
    ]


def test_api_quickbooks_export(client):
    r = client.post("/api/export", json={"transactions": ROWS, "format": "quickbooks", "currency": "USD"})
    assert r.status_code == 200
    assert 'filename="statement-quickbooks.csv"' in r.headers["content-disposition"]
    assert r.headers["content-type"].startswith("text/csv")
    assert r.text.splitlines()[0] == "Date,Description,Amount"
    # Rows only: no opening/closing balance rows, no category or balance columns.
    assert len(r.text.splitlines()) == 3
    assert "Food" not in r.text and "95.50" not in r.text


def test_api_xero_export(client):
    r = client.post("/api/export", json={"transactions": ROWS, "format": "xero", "currency": "NZD"})
    assert r.status_code == 200
    assert 'filename="statement-xero.csv"' in r.headers["content-disposition"]
    assert r.text.splitlines()[1] == "01/01/2024,-4.50,Coffee,,"


def test_api_bulk_quickbooks_combines_rows(client):
    statements = [
        {"name": "jan.pdf", "transactions": ROWS[:1]},
        {"name": "feb.pdf", "transactions": [{"date": "2024-02-01", "description": "Rent", "amount": "900", "type": "debit"}]},
    ]
    r = client.post("/api/export/bulk", json={"statements": statements, "format": "quickbooks"})
    assert r.status_code == 200
    assert 'filename="statements-combined-quickbooks.csv"' in r.headers["content-disposition"]
    assert r.text.splitlines() == [
        "Date,Description,Amount",
        "01/01/2024,Coffee,-4.50",
        "02/01/2024,Rent,-900.00",
    ]


def test_api_rejects_unknown_format(client):
    r = client.post("/api/export", json={"transactions": ROWS, "format": "ofx"})
    assert r.status_code == 422


def test_blog_feature_posts_get_their_page_link():
    from services.blog_generator import QUICKBOOKS_PAGE, XERO_PAGE, _ensure_feature_link

    data = {"body_markdown": "Body."}
    _ensure_feature_link({"feature": "xero"}, data)
    assert f"]({XERO_PAGE})" in data["body_markdown"]
    linked = {"body_markdown": f"See [the export]({QUICKBOOKS_PAGE})."}
    _ensure_feature_link({"feature": "quickbooks"}, linked)
    assert linked["body_markdown"] == f"See [the export]({QUICKBOOKS_PAGE})."
