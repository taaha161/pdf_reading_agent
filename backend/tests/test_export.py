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


TOTALS_ROWS = [
    {"date": "01 Jul", "description": "Salary", "amount": "1,000.50", "type": "credit", "category": "Income"},
    {"date": "02 Jul", "description": "Rent", "amount": "400", "type": "debit", "category": "Housing"},
    {"date": "03 Jul", "description": "Groceries", "amount": "99.25", "type": "debit", "category": "Groceries"},
    {"date": "04 Jul", "description": "Odd row", "amount": "n/a", "type": "debit", "category": "Other"},
]


def test_export_totals_math():
    from services.csv_export import export_totals

    assert export_totals(TOTALS_ROWS) == (4, 1000.5, 499.25)


def test_xlsx_totals_block_has_formulas_and_cached_values():
    import io
    import zipfile

    from services.xlsx_export import transactions_to_xlsx

    data = transactions_to_xlsx(TOTALS_ROWS, include_totals=True)
    ws = load_workbook(io.BytesIO(data)).active
    # rows 2-5 data, row 6 blank, rows 7-10 totals (label in Description, value in Amount)
    assert ws["B6"].value is None and ws["C6"].value is None
    assert [ws[f"B{r}"].value for r in range(7, 11)] == [
        "Transactions", "Total money in (credits)", "Total money out (debits)", "Net (in - out)",
    ]
    assert ws["C8"].value == '=SUMIFS(C2:C5,D2:D5,"credit")'
    assert ws["C9"].value == '=SUMIFS(C2:C5,D2:D5,"debit")'
    assert ws["C10"].value == "=C8-C9"
    # Cached results are stored so phone viewers that don't calculate still show numbers.
    cached = load_workbook(io.BytesIO(data), data_only=True).active
    assert [cached[f"C{r}"].value for r in range(7, 11)] == [4, 1000.5, 499.25, 501.25]
    assert ws.auto_filter.ref == "A1:E5"  # filter covers the data only
    # Uncategorized variant keeps the same columns for description/amount/type.
    ws2 = load_workbook(io.BytesIO(transactions_to_xlsx(TOTALS_ROWS, False, True))).active
    assert ws2["C8"].value == '=SUMIFS(C2:C5,D2:D5,"credit")'
    # Default stays rows-only for accounting imports.
    plain = load_workbook(io.BytesIO(transactions_to_xlsx(TOTALS_ROWS))).active
    assert plain.max_row == 5
    assert "sharedStrings.xml" in " ".join(zipfile.ZipFile(io.BytesIO(data)).namelist())


def test_csv_totals_rows():
    from services.csv_export import transactions_to_csv

    lines = transactions_to_csv(TOTALS_ROWS, include_totals=True).splitlines()
    assert lines[-5:] == [
        ",,,,",
        ",Transactions,4,,",
        ",Total money in (credits),1000.50,,",
        ",Total money out (debits),499.25,,",
        ",Net (in - out),501.25,,",
    ]
    assert len(transactions_to_csv(TOTALS_ROWS).splitlines()) == 5  # default: header + rows only


def test_export_endpoint_include_totals(client):
    r = client.post("/api/export", json={"transactions": TOTALS_ROWS, "format": "csv", "include_totals": True})
    assert r.status_code == 200 and "Total money in (credits),1000.50" in r.text
    r = client.post("/api/export", json={"transactions": TOTALS_ROWS, "format": "csv"})
    assert "Total money" not in r.text
