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
    # Laid out like a statement: separate Debit and Credit columns, sizes only.
    assert r.text.splitlines()[0] == "date,description,debit,credit,category"
    assert "Coffee,4.50,,Food" in r.text
    assert "=1+1,,1200.00," in r.text


def test_csv_without_categories(client):
    r = _export(client, format="csv", include_categories=False)
    assert 'filename="statement-uncategorized.csv"' in r.headers["content-disposition"]
    assert r.text.splitlines()[0] == "date,description,debit,credit"
    assert "Food" not in r.text


def test_xlsx_with_categories(client):
    r = _export(client, format="xlsx", include_categories=True)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/vnd.openxmlformats")
    ws = load_workbook(io.BytesIO(r.content)).active
    assert [c.value for c in ws[1]] == ["Date", "Description", "Debit", "Credit", "Category"]
    assert ws["C2"].value == 4.5 and ws["D2"].value is None
    assert ws["C3"].value is None and ws["D3"].value == 1200.0
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
    assert [c.value for c in ws[1]] == ["Date", "Description", "Debit", "Credit", "Category"]
    assert ws["B2"].value == "=HYPERLINK(\"x\")" and ws["B2"].data_type == "s"  # text, not a formula
    assert ws["D2"].value == 1000.0 and ws["D2"].number_format == "#,##0.00"
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
    # Money in sums the Credit column (D), money out the Debit column (C).
    assert ws["C12"].value == "=SUMPRODUCT(--(E2:E7=A12),D2:D7)"
    assert ws["D13"].value == '=SUMPRODUCT(--(E2:E7=""),C2:C7)'
    assert ws["E12"].value == "=C12-D12"
    assert ws["B15"].value == "=ROWS(A2:A7)"
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
    assert ws2["A10"].value == "All categories" and ws2["C10"].value == "=SUM(D2:D7)"
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
    assert lines[0] == "date,description,debit,credit,category,sub-category"
    assert lines[1] == "01 Jul,From John,,100.00,Income,John"
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
    assert [c.value for c in ws[1]] == ["Date", "Description", "Debit", "Credit", "Category", "Sub-category"]
    assert ws["F4"].value == "Alice"
    # rows 2-4 data, 5 blank, 6 category header, 7-8 categories (no "All categories"), 9 blank, 10 sub-category header
    assert [ws[f"A{r}"].value for r in range(6, 10)] == ["Category", "Income", "Transfers", None]
    assert [c.value for c in ws[10]][:5] == ["Sub-category", "Transactions", "Money in", "Money out", "Net"]
    assert [ws[f"A{r}"].value for r in range(11, 14)] == ["John", "Alice", "Net total"]
    assert ws["C11"].value == "=SUMPRODUCT(--(F2:F4=A11),D2:D4)"
    cached = load_workbook(io.BytesIO(data), data_only=True).active
    assert [[cached.cell(r, c).value for c in range(2, 6)] for r in range(11, 14)] == [
        [2, 100, 30, 70], [1, 0, 50.5, -50.5], [3, 100, 80.5, 19.5],
    ]


def test_export_endpoint_keeps_group_and_omits_it_when_blank(client):
    r = client.post("/api/export", json={"transactions": GROUPED_ROWS, "format": "csv", "include_totals": True})
    assert r.status_code == 200 and "Net total,3,100.00,80.50,19.50" in r.text
    r = client.post("/api/export", json={"transactions": TOTALS_ROWS, "format": "csv", "include_totals": True})
    assert r.text.splitlines()[0] == "date,description,debit,credit,category" and "Net total" not in r.text


BALANCE_ROWS = [
    {"date": "01 Jul", "description": "Salary", "amount": "1,000.00", "type": "credit", "category": "Income", "balance": "1500.00"},
    {"date": "02 Jul", "description": "Overdrawn", "amount": "2000", "type": "debit", "category": "Other", "balance": "-500.00"},
]


def test_balance_column_when_statement_has_balances(client):
    r = client.post("/api/export", json={"transactions": BALANCE_ROWS, "format": "csv"})
    assert r.text.splitlines() == [
        "date,description,debit,credit,balance,category",
        "01 Jul,Opening balance,,,500.00,",
        "01 Jul,Salary,,1000.00,1500.00,Income",
        "02 Jul,Overdrawn,2000.00,,-500.00,Other",
        "02 Jul,Closing balance,,,-500.00,",
    ]
    r = client.post("/api/export", json={"transactions": BALANCE_ROWS, "format": "xlsx", "include_totals": True})
    ws = load_workbook(io.BytesIO(r.content)).active
    assert [c.value for c in ws[1]] == ["Date", "Description", "Debit", "Credit", "Balance", "Category"]
    assert [ws["E2"].value, ws["E3"].value] == [1500.0, -500.0]
    assert ws["E3"].number_format == "#,##0.00"
    # Totals still read the Debit/Credit columns, with Category now in F.
    assert ws["C6"].value == "=SUMPRODUCT(--(F2:F3=A6),D2:D3)"


def test_balance_rows_in_excel_download(client):
    r = client.post("/api/export", json={"transactions": BALANCE_ROWS, "format": "xlsx"})
    ws = load_workbook(io.BytesIO(r.content)).active
    rows = [[c.value for c in row] for row in ws.iter_rows(min_row=2, max_col=5)]
    assert rows == [
        ["01 Jul", "Opening balance", None, None, 500.0],
        ["01 Jul", "Salary", None, 1000.0, 1500.0],
        ["02 Jul", "Overdrawn", 2000.0, None, -500.0],
        ["02 Jul", "Closing balance", None, None, -500.0],
    ]
    assert ws.auto_filter.ref == "A1:F5"


def test_balance_rows_follow_newest_first_statements():
    from services.csv_export import transactions_to_csv

    rows = list(reversed(BALANCE_ROWS))
    lines = transactions_to_csv(rows).splitlines()
    assert lines[1] == "02 Jul,Closing balance,,,-500.00,"
    assert lines[-1] == "01 Jul,Opening balance,,,500.00,"


def test_no_balance_rows_when_balances_dont_add_up():
    from services.csv_export import transactions_to_csv

    # A filtered subset (a row missing between them) or edited amounts: balances no longer chain.
    rows = [dict(BALANCE_ROWS[0]), {**BALANCE_ROWS[1], "amount": "50"}]
    assert "Opening balance" not in transactions_to_csv(rows)
    # Statements without balances get no Balance column and no balance rows.
    plain = [{k: v for k, v in r.items() if k != "balance"} for r in BALANCE_ROWS]
    assert "Opening balance" not in transactions_to_csv(plain)


def test_opening_closing_credit_card_sign():
    from services.balances import opening_closing

    # Credit card: balance is what you owe, so a purchase (debit) raises it.
    rows = [
        {"amount": "100", "type": "debit", "balance": "300.00"},
        {"amount": "50", "type": "credit", "balance": "250.00"},
    ]
    assert opening_closing(rows) == (False, 200.0, 250.0)
    assert opening_closing([]) is None
    assert opening_closing([{"amount": "10", "type": "debit", "balance": ""}]) is None


def test_ledger_csv_keeps_stored_shape():
    from services.csv_export import transactions_to_csv

    assert transactions_to_csv(BALANCE_ROWS, ledger=True).splitlines()[:2] == [
        "date,description,amount,type,category",
        "01 Jul,Salary,\"1,000.00\",credit,Income",
    ]


RECON = {
    "status": "mismatch", "total_credits": 1200.0, "total_debits": 4.5,
    "opening_balance": 100.0, "closing_balance": 1300.0,
    "checks": [
        {"key": "opening", "status": "skipped", "expected": 100.0, "actual": None},
        {"key": "credits", "status": "pass", "expected": 1200.0, "actual": 1200.0, "difference": 0.0},
        {"key": "debits", "status": "fail", "expected": 4.5, "actual": 4.5, "difference": 0.0},
    ],
    "hints": [{"kind": "missing_row", "from_row": 0, "to_row": 1, "amount": 4.5, "direction": "debit"}],
}


def test_xlsx_reconciliation_sheet(client):
    r = _export(client, format="xlsx", reconciliation=RECON)
    wb = load_workbook(io.BytesIO(r.content))
    assert wb.sheetnames == ["Transactions", "Reconciliation"]
    ws = wb["Reconciliation"]
    assert ws["A1"].value == "Doesn't add up"
    assert [c.value for c in ws[4]] == ["Check", "Statement says", "We extracted", "Difference", "Result"]
    assert ws["A5"].value == "Opening balance" and ws["C5"].value is None and ws["E5"].value == "Not checked"
    # Money in is a live SUM over the Transactions sheet's Credit column.
    assert ws["C6"].value == "=SUM(Transactions!D2:D3)"
    assert ws["D6"].value == "=B6-C6" and ws["E6"].value == "Matches"
    assert ws["E7"].value == "Doesn't match"
    assert ws["A10"].value == "A debit of 4.50 may be missing between rows 1 and 2."


def test_xlsx_without_reconciliation_has_one_sheet(client):
    wb = load_workbook(io.BytesIO(_export(client, format="xlsx").content))
    assert wb.sheetnames == ["Transactions"]
