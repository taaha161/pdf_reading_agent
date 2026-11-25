"""Tests for /api/export/bulk (combined download for a bulk upload)."""
import io

from openpyxl import load_workbook

from services.xlsx_export import _sheet_names

JAN = [
    {"date": "2024-01-01", "description": "Coffee", "amount": "-4.50", "type": "debit", "category": "Food"},
    {"date": "2024-01-02", "description": "Salary", "amount": "1,200.00", "type": "credit", "category": "Income"},
]
FEB = [{"date": "2024-02-01", "description": "Rent", "amount": "900", "type": "debit", "category": "Housing"}]


def _bulk(client, statements=None, **body):
    statements = statements or [
        {"name": "chase-jan.pdf", "transactions": JAN},
        {"name": "chase-feb.pdf", "transactions": FEB},
    ]
    return client.post("/api/export/bulk", json={"statements": statements, **body})


def test_csv_has_statement_column(client):
    r = _bulk(client, format="csv")
    assert r.status_code == 200
    assert 'filename="statements-combined.csv"' in r.headers["content-disposition"]
    lines = r.text.splitlines()
    assert lines[0] == "statement,date,description,debit,credit,category"
    assert lines[1] == "chase-jan.pdf,2024-01-01,Coffee,4.50,,Food"
    assert lines[3] == "chase-feb.pdf,2024-02-01,Rent,900.00,,Housing"
    assert len(lines) == 4


def test_csv_neutralizes_formula_file_names(client):
    r = _bulk(client, [{"name": "=cmd.pdf", "transactions": FEB}], format="csv")
    assert r.text.splitlines()[1].startswith("'=cmd.pdf,")


def test_csv_without_categories(client):
    r = _bulk(client, format="csv", include_categories=False)
    assert 'filename="statements-combined-uncategorized.csv"' in r.headers["content-disposition"]
    assert r.text.splitlines()[0] == "statement,date,description,debit,credit"


def test_xlsx_combined_sheet_then_one_per_statement(client):
    r = _bulk(client, format="xlsx")
    assert r.status_code == 200
    wb = load_workbook(io.BytesIO(r.content))
    assert wb.sheetnames == ["All statements", "chase-jan", "chase-feb"]
    combined = wb["All statements"]
    assert [c.value for c in combined[1]] == ["Statement", "Date", "Description", "Debit", "Credit", "Category"]
    assert combined.max_row == 4
    assert combined["A4"].value == "chase-feb.pdf" and combined["D4"].value == 900.0
    jan = wb["chase-jan"]
    assert [c.value for c in jan[1]] == ["Date", "Description", "Debit", "Credit", "Category"]
    assert jan["D3"].value == 1200.0


def test_sheet_names_are_valid_and_unique():
    names = _sheet_names(["a/b:c.pdf", "a/b:c.pdf", "x" * 40 + ".pdf", "All statements", "[]"])
    assert names[0] == "a b c"
    assert names[1] == "a b c (2)"
    assert len(names[2]) == 31
    assert names[3] == "All statements (2)"
    assert names[4] == "Statement"
    assert len(set(n.lower() for n in names)) == len(names)


def test_rejects_empty_and_too_many_statements(client):
    assert client.post("/api/export/bulk", json={"statements": []}).status_code == 422
    many = [{"name": f"s{i}.pdf", "transactions": FEB} for i in range(51)]
    assert _bulk(client, many).status_code == 422
