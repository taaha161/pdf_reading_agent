"""Turn list of transaction dicts into an Excel (.xlsx) workbook.

Written with XlsxWriter, which stores text in a shared-strings table the way Excel does.
openpyxl 3.1 writes inline strings instead; that is valid, but many phone viewers
(e.g. Android file/document previewers) ignore them and show only the number cells.
"""
import io
from typing import Any

import xlsxwriter
from xlsxwriter.utility import xl_col_to_name

from services.csv_export import (
    ALL_CATEGORIES,
    NO_CATEGORY,
    TOTALS_HEADER,
    amount_value,
    category_totals,
    export_fields,
    export_totals,
)

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

_HEADERS = {"date": "Date", "description": "Description", "amount": "Amount", "type": "Type", "category": "Category"}
_WIDTHS = {"date": 12, "description": 48, "amount": 14, "type": 10, "category": 20}
_MONEY_FORMAT = "#,##0.00"


def _new_workbook(sheet_name: str):
    out = io.BytesIO()
    # in_memory: no temp files; strings_to_*: False so text like "=1+1" or "http://..." stays plain text.
    wb = xlsxwriter.Workbook(
        out,
        {
            "in_memory": True,
            "strings_to_formulas": False,
            "strings_to_urls": False,
            "strings_to_numbers": False,
        },
    )
    ws = wb.add_worksheet(sheet_name)
    header = wb.add_format({"bold": True, "font_color": "#FFFFFF", "bg_color": "#2563EB", "valign": "vcenter"})
    money = wb.add_format({"num_format": _MONEY_FORMAT})
    return out, wb, ws, header, money


def _write_totals(wb, ws, transactions: list[dict[str, Any]], fields: list[str], header) -> None:
    """Totals table under the rows (after one blank row), in columns A-E:
    Category | Transactions | Money in | Money out | Net, one row per category, then "All categories".

    Live formulas (they follow edits to the rows) with cached results, because phone viewers don't
    calculate formulas and would otherwise show 0 or nothing. SUMPRODUCT with "=" is used instead of
    SUMIFS so category names are matched exactly (no * ? ~ wildcards or ">"/"<" operators) and text
    amounts count as 0.
    """
    first, last = 2, len(transactions) + 1  # Excel row numbers of the data

    def rng(field: str) -> str:
        col = xl_col_to_name(fields.index(field))
        return f"{col}{first}:{col}{last}"

    amounts, types = rng("amount"), rng("type")
    has_categories = "category" in fields
    groups = category_totals(transactions) if has_categories else []

    money = wb.add_format({"num_format": _MONEY_FORMAT})
    bold = wb.add_format({"bold": True, "top": 1})
    bold_money = wb.add_format({"bold": True, "top": 1, "num_format": _MONEY_FORMAT})

    top = last + 1  # 0-based row index of the table header (row `last` is the blank spacer)
    for col, label in enumerate(TOTALS_HEADER):
        ws.write_string(top, col, label, header)

    for i, (name, count, money_in, money_out) in enumerate(groups):
        r = top + 1 + i  # 0-based; Excel row is r + 1
        match = f'--({rng("category")}="")' if name == NO_CATEGORY else f"--({rng('category')}=A{r + 1})"
        ws.write_string(r, 0, name)
        ws.write_formula(r, 1, f"=SUMPRODUCT({match})", None, count)
        ws.write_formula(r, 2, f'=SUMPRODUCT({match},--({types}="credit"),{amounts})', money, money_in)
        ws.write_formula(r, 3, f'=SUMPRODUCT({match},--({types}="debit"),{amounts})', money, money_out)
        ws.write_formula(r, 4, f"=C{r + 1}-D{r + 1}", money, round(money_in - money_out, 2))

    r = top + 1 + len(groups)  # the "All categories" row
    count, credit, debit = export_totals(transactions)
    ws.write_string(r, 0, ALL_CATEGORIES, bold)
    ws.write_formula(r, 1, f"=COUNTA({types})", bold, count)
    ws.write_formula(r, 2, f'=SUMPRODUCT(--({types}="credit"),{amounts})', bold_money, credit)
    ws.write_formula(r, 3, f'=SUMPRODUCT(--({types}="debit"),{amounts})', bold_money, debit)
    ws.write_formula(r, 4, f"=C{r + 1}-D{r + 1}", bold_money, round(credit - debit, 2))

    # Column A holds dates above and category names here; widen it to fit both (capped).
    longest = max([len(ALL_CATEGORIES)] + [len(g[0]) for g in groups])
    ws.set_column(0, 0, max(_WIDTHS["date"], min(longest + 2, 32)))
    ws.set_column(3, 3, max(_WIDTHS["type"], 14))  # money out lands in the narrow Type column


def transactions_to_xlsx(
    transactions: list[dict[str, Any]], include_categories: bool = True, include_totals: bool = False
) -> bytes:
    """Return .xlsx bytes: bold frozen header, numeric amounts, sized columns, autofilter.

    include_totals adds a per-category totals table and an "All categories" row under the rows
    (off by default: accounting imports expect rows only).
    """
    fields = export_fields(include_categories)
    out, wb, ws, header, money = _new_workbook("Transactions")

    for col, field in enumerate(fields):
        ws.write_string(0, col, _HEADERS[field], header)
        ws.set_column(col, col, _WIDTHS[field])

    for row, tx in enumerate(transactions, start=1):
        for col, field in enumerate(fields):
            value = amount_value(tx.get(field)) if field == "amount" else str(tx.get(field) or "")
            if isinstance(value, float):
                ws.write_number(row, col, value, money)
            elif value:
                ws.write_string(row, col, value)

    ws.freeze_panes(1, 0)
    ws.autofilter(0, 0, max(len(transactions), 1), len(fields) - 1)
    if include_totals and transactions:
        _write_totals(wb, ws, transactions, fields, header)
    wb.close()
    return out.getvalue()


def summary_to_xlsx(summary: list[tuple[str, float]]) -> bytes:
    """Return .xlsx bytes for the category totals table (numeric totals)."""
    out, wb, ws, header, money = _new_workbook("Summary")
    ws.write_string(0, 0, "Category", header)
    ws.write_string(0, 1, "Total", header)
    for row, (category, total) in enumerate(summary, start=1):
        ws.write_string(row, 0, str(category))
        ws.write_number(row, 1, round(total, 2), money)
    ws.set_column(0, 0, 28)
    ws.set_column(1, 1, 16)
    ws.freeze_panes(1, 0)
    wb.close()
    return out.getvalue()
