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
    {"date": "04 Jul", "description": "Refund", "amount": "10", "type": "credit", "category": "groceries"},
    {"date": "05 Jul", "description": "Odd row", "amount": "n/a", "type": "debit", "category": ">100*"},
    {"date": "06 Jul", "description": "No cat", "amount": "5", "type": "debit", "category": ""},
]


def test_category_totals_group_case_insensitively_biggest_first():
    from services.csv_export import category_totals, export_totals

    assert export_totals(TOTALS_ROWS) == (6, 1010.5, 504.25)
    assert category_totals(TOTALS_ROWS) == [
        ("Income", 1, 1000.5, 0.0),
        ("Housing", 1, 0.0, 400.0),
        ("Groceries", 2, 10.0, 99.25),
        ("(no category)", 1, 0.0, 5.0),
        (">100*", 1, 0.0, 0.0),
    ]


def test_xlsx_category_totals_table():
    import io

    from services.xlsx_export import transactions_to_xlsx

    data = transactions_to_xlsx(TOTALS_ROWS, include_totals=True)
    ws = load_workbook(io.BytesIO(data)).active
    # rows 2-7 data, row 8 blank, row 9 table header, rows 10-14 categories, row 15 all categories
    assert all(c.value is None for c in ws[8])
    assert [c.value for c in ws[9]] == ["Category", "Transactions", "Money in", "Money out", "Net"]
    assert [ws[f"A{r}"].value for r in range(10, 16)] == [
        "Income", "Housing", "Groceries", "(no category)", ">100*", "All categories",
    ]
    # Exact match on the category cell (no SUMIFS wildcards/operators), blank category matched as "".
    assert ws["C12"].value == '=SUMPRODUCT(--(E2:E7=A12),--(D2:D7="credit"),C2:C7)'
    assert ws["D13"].value == '=SUMPRODUCT(--(E2:E7=""),--(D2:D7="debit"),C2:C7)'
    assert ws["E12"].value == "=C12-D12"
    assert ws["B15"].value == "=COUNTA(D2:D7)"
    # Cached results so phone viewers show numbers without calculating.
    cached = load_workbook(io.BytesIO(data), data_only=True).active
    assert [[cached.cell(r, c).value for c in range(2, 6)] for r in range(10, 16)] == [
        [1, 1000.5, 0, 1000.5],
        [1, 0, 400, -400],
        [2, 10, 99.25, -89.25],
        [1, 0, 5, -5],
        [1, 0, 0, 0],
        [6, 1010.5, 504.25, 506.25],
    ]
    assert ws.auto_filter.ref == "A1:E7"  # filter covers the data only
    # Without a category column only the "All categories" row is written.
    ws2 = load_workbook(io.BytesIO(transactions_to_xlsx(TOTALS_ROWS, False, True))).active
    assert ws2["A10"].value == "All categories" and ws2["C10"].value == '=SUMPRODUCT(--(D2:D7="credit"),C2:C7)'
    # Default stays rows-only for accounting imports.
    assert load_workbook(io.BytesIO(transactions_to_xlsx(TOTALS_ROWS))).active.max_row == 7


def test_csv_category_totals_table():
    from services.csv_export import transactions_to_csv

    lines = transactions_to_csv(TOTALS_ROWS, include_totals=True).splitlines()
    assert lines[-8:] == [
        "",
        "Category,Transactions,Money in,Money out,Net",
        "Income,1,1000.50,0.00,1000.50",
        "Housing,1,0.00,400.00,-400.00",
        "Groceries,2,10.00,99.25,-89.25",
        "(no category),1,0.00,5.00,-5.00",
        ">100*,1,0.00,0.00,0.00",
        "All categories,6,1010.50,504.25,506.25",
    ]
    assert len(transactions_to_csv(TOTALS_ROWS).splitlines()) == 7  # default: header + rows only


def test_export_endpoint_include_totals(client):
    r = client.post("/api/export", json={"transactions": TOTALS_ROWS, "format": "csv", "include_totals": True})
    assert r.status_code == 200 and "All categories,6,1010.50,504.25,506.25" in r.text
    r = client.post("/api/export", json={"transactions": TOTALS_ROWS, "format": "csv"})
    assert "All categories" not in r.text


GROUPED_ROWS = [
    {"date": "01 Jul", "description": "From John", "amount": "100", "type": "credit", "category": "Income", "group": "John"},
    {"date": "02 Jul", "description": "To John", "amount": "30", "type": "debit", "category": "Transfers", "group": "John"},
    {"date": "03 Jul", "description": "To Alice", "amount": "50.5", "type": "debit", "category": "Transfers", "group": "Alice"},
]


def test_csv_group_column_and_group_totals():
    from services.csv_export import transactions_to_csv

    lines = transactions_to_csv(GROUPED_ROWS, include_totals=True).splitlines()
    assert lines[0] == "date,description,amount,type,category,sub-category"
    assert lines[1] == "01 Jul,From John,100,credit,Income,John"
    assert "All categories" not in "\n".join(lines)
    assert lines[-9:] == [
        "",
        "Category,Transactions,Money in,Money out,Net",
        "Income,1,100.00,0.00,100.00",
        "Transfers,2,0.00,80.50,-80.50",
        "",
        "Sub-category,Transactions,Money in,Money out,Net",
        "John,2,100.00,30.00,70.00",
        "Alice,1,0.00,50.50,-50.50",
        "Net total,3,100.00,80.50,19.50",
    ]


def test_xlsx_group_column_and_group_totals():
    from services.xlsx_export import transactions_to_xlsx

    data = transactions_to_xlsx(GROUPED_ROWS, include_totals=True)
    ws = load_workbook(io.BytesIO(data)).active
    assert [c.value for c in ws[1]] == ["Date", "Description", "Amount", "Type", "Category", "Sub-category"]
    assert ws["F4"].value == "Alice"
    # rows 2-4 data, 5 blank, 6 category header, 7-8 categories (no "All categories"), 9 blank, 10 sub-category header
    assert [ws[f"A{r}"].value for r in range(6, 10)] == ["Category", "Income", "Transfers", None]
    assert [c.value for c in ws[10]][:5] == ["Sub-category", "Transactions", "Money in", "Money out", "Net"]
    assert [ws[f"A{r}"].value for r in range(11, 14)] == ["John", "Alice", "Net total"]
    assert ws["C11"].value == '=SUMPRODUCT(--(F2:F4=A11),--(D2:D4="credit"),C2:C4)'
    cached = load_workbook(io.BytesIO(data), data_only=True).active
    assert [[cached.cell(r, c).value for c in range(2, 6)] for r in range(11, 14)] == [
        [2, 100, 30, 70], [1, 0, 50.5, -50.5], [3, 100, 80.5, 19.5],
    ]


def test_export_endpoint_keeps_group_and_omits_it_when_blank(client):
    r = client.post("/api/export", json={"transactions": GROUPED_ROWS, "format": "csv", "include_totals": True})
    assert r.status_code == 200 and "Net total,3,100.00,80.50,19.50" in r.text
    r = client.post("/api/export", json={"transactions": TOTALS_ROWS, "format": "csv", "include_totals": True})
    assert r.text.splitlines()[0] == "date,description,amount,type,category" and "Net total" not in r.text
