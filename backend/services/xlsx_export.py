"""Turn list of transaction dicts into an Excel (.xlsx) workbook.

Written with XlsxWriter, which stores text in a shared-strings table the way Excel does.
openpyxl 3.1 writes inline strings instead; that is valid, but many phone viewers
(e.g. Android file/document previewers) ignore them and show only the number cells.
"""
import io
from typing import Any

import xlsxwriter
from xlsxwriter.utility import xl_col_to_name

from services.csv_export import TOTAL_LABELS, amount_value, export_fields, export_totals

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


def _write_totals(wb, ws, transactions: list[dict[str, Any]], fields: list[str]) -> None:
    """Totals block under the rows: label in Description, value in Amount.

    Live SUMIFS formulas (they follow edits) with cached results, because phone viewers don't
    calculate formulas and would otherwise show 0 or nothing.
    """
    label_col, amount_col, type_col = (fields.index(f) for f in ("description", "amount", "type"))
    first, last = 2, len(transactions) + 1  # Excel row numbers of the data
    amounts = f"{xl_col_to_name(amount_col)}{first}:{xl_col_to_name(amount_col)}{last}"
    types = f"{xl_col_to_name(type_col)}{first}:{xl_col_to_name(type_col)}{last}"
    bold = wb.add_format({"bold": True})
    bold_money = wb.add_format({"bold": True, "num_format": _MONEY_FORMAT, "top": 1})
    bold_count = wb.add_format({"bold": True, "top": 1})

    count, credit, debit = export_totals(transactions)
    start = last + 1  # 0-based index of the row after a blank spacer row
    in_ref, out_ref = f"{xl_col_to_name(amount_col)}{start + 2}", f"{xl_col_to_name(amount_col)}{start + 3}"
    cells = (
        (f'=COUNTA({xl_col_to_name(type_col)}{first}:{xl_col_to_name(type_col)}{last})', count, bold_count),
        (f'=SUMIFS({amounts},{types},"credit")', credit, bold_money),
        (f'=SUMIFS({amounts},{types},"debit")', debit, bold_money),
        (f"={in_ref}-{out_ref}", round(credit - debit, 2), bold_money),
    )
    for i, (label, (formula, cached, fmt)) in enumerate(zip(TOTAL_LABELS, cells)):
        ws.write_string(start + i, label_col, label, bold)
        ws.write_formula(start + i, amount_col, formula, fmt, cached)


def transactions_to_xlsx(
    transactions: list[dict[str, Any]], include_categories: bool = True, include_totals: bool = False
) -> bytes:
    """Return .xlsx bytes: bold frozen header, numeric amounts, sized columns, autofilter.

    include_totals adds count / money in / money out / net under the rows (off by default:
    accounting imports expect rows only).
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
        _write_totals(wb, ws, transactions, fields)
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
