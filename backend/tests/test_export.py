"""Tests for /api/export (CSV / Excel, with or without categories)."""
import io

from openpyxl import load_workbook

ROWS = [
    {"date": "2024-01-01", "description": "Coffee", "amount": "-4.50", "type": "debit", "category": "Food"},
    {"date": "2024-01-02", "description": "=1+1", "amount": "1,200.00", "type": "credit", "category": None},
]


def _export(client, **body):
    return client.post("/api/export", json={"transactions": ROWS, **body})


def test_csv_with_categories(client):
    r = _export(client, format="csv", include_categories=True)
    assert r.status_code == 200
    assert 'filename="statement.csv"' in r.headers["content-disposition"]
    assert r.text.splitlines()[0] == "date,description,amount,type,category"
    assert "Coffee,-4.50,debit,Food" in r.text


def test_csv_without_categories(client):
    r = _export(client, format="csv", include_categories=False)
    assert 'filename="statement-uncategorized.csv"' in r.headers["content-disposition"]
    assert r.text.splitlines()[0] == "date,description,amount,type"
    assert "Food" not in r.text


def test_xlsx_with_categories(client):
    r = _export(client, format="xlsx", include_categories=True)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/vnd.openxmlformats")
    ws = load_workbook(io.BytesIO(r.content)).active
    assert [c.value for c in ws[1]] == ["Date", "Description", "Amount", "Type", "Category"]
    assert ws["C2"].value == -4.5 and ws["C3"].value == 1200.0
    assert ws["B3"].value == "=1+1" and ws["B3"].data_type == "s"  # text, not a formula
    assert ws["E3"].value in (None, "")


def test_xlsx_without_categories(client):
    r = _export(client, format="xlsx", include_categories=False)
    assert 'filename="statement-uncategorized.xlsx"' in r.headers["content-disposition"]
    ws = load_workbook(io.BytesIO(r.content)).active
    assert ws.max_column == 4


def test_rejects_unknown_format(client):
    assert _export(client, format="pdf").status_code == 422


SUMMARY_ROWS = [
    {"date": "2024-01-01", "description": "Coffee", "amount": "-4.50", "type": "debit", "category": "Food"},
    {"date": "2024-01-03", "description": "Lunch", "amount": "10.00", "type": "debit", "category": "Food"},
    {"date": "2024-01-02", "description": "Salary", "amount": "1,200.00", "type": "credit", "category": "Income"},
    {"date": "2024-01-04", "description": "Misc", "amount": "3.00", "type": "debit", "category": "=cmd"},
]


def _export_summary(client, fmt):
    return client.post("/api/export", json={"transactions": SUMMARY_ROWS, "format": fmt, "kind": "summary"})


def test_summary_csv(client):
    r = _export_summary(client, "csv")
    assert r.status_code == 200
    assert 'filename="statement-summary.csv"' in r.headers["content-disposition"]
    assert r.text.splitlines() == ["category,total", "Income,1200.00", "Food,14.50", "=cmd,3.00"]


def test_summary_xlsx(client):
    r = _export_summary(client, "xlsx")
    assert r.status_code == 200
    assert 'filename="statement-summary.xlsx"' in r.headers["content-disposition"]
    ws = load_workbook(io.BytesIO(r.content)).active
    assert [c.value for c in ws[1]] == ["Category", "Total"]
    assert [(ws.cell(i, 1).value, ws.cell(i, 2).value) for i in range(2, 5)] == [
        ("Income", 1200.0), ("Food", 14.5), ("=cmd", 3.0)
    ]
    assert ws["A4"].data_type == "s"  # text, not a formula


def test_rejects_unknown_kind(client):
    r = client.post("/api/export", json={"transactions": ROWS, "kind": "pivot"})
    assert r.status_code == 422


def test_xlsx_text_uses_shared_strings_for_phone_viewers():
    """Phone viewers (e.g. Android previewers) skip inline strings and show only numbers."""
    import io
    import zipfile

    from services.xlsx_export import summary_to_xlsx, transactions_to_xlsx

    rows = [
        {"date": "02 Jul 2025", "description": "=HYPERLINK(\"x\")", "amount": "1,000.00", "type": "credit", "category": "Income"},
        {"date": "03 Jul 2025", "description": "http://example.com", "amount": "n/a", "type": "debit", "category": "Other"},
    ]
    for data in (transactions_to_xlsx(rows), summary_to_xlsx([("Income", 1000.0)])):
        z = zipfile.ZipFile(io.BytesIO(data))
        assert "xl/sharedStrings.xml" in z.namelist()
        assert "inlineStr" not in z.read("xl/worksheets/sheet1.xml").decode()

    ws = load_workbook(io.BytesIO(transactions_to_xlsx(rows))).active
    assert [c.value for c in ws[1]] == ["Date", "Description", "Amount", "Type", "Category"]
    assert ws["B2"].value == "=HYPERLINK(\"x\")" and ws["B2"].data_type == "s"  # text, not a formula
    assert ws["C2"].value == 1000.0 and ws["C2"].number_format == "#,##0.00"
    assert ws["C3"].value == "n/a" and ws["B3"].value == "http://example.com"
    assert ws.freeze_panes == "A2" and ws.auto_filter.ref == "A1:E3"
