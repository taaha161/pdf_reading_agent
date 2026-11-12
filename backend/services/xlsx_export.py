"""Turn list of transaction dicts into an Excel (.xlsx) workbook.

Written with XlsxWriter, which stores text in a shared-strings table the way Excel does.
openpyxl 3.1 writes inline strings instead; that is valid, but many phone viewers
(e.g. Android file/document previewers) ignore them and show only the number cells.
"""
import io
import re
from typing import Any

import xlsxwriter

from services.csv_export import export_fields

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

_HEADERS = {"date": "Date", "description": "Description", "amount": "Amount", "type": "Type", "category": "Category"}
_WIDTHS = {"date": 12, "description": 48, "amount": 14, "type": 10, "category": 20}
_NUMBER_RE = re.compile(r"^-?\d+(\.\d+)?$")
_MONEY_FORMAT = "#,##0.00"


def _amount_value(raw: Any) -> float | str:
    """Real number when the amount parses (so Excel can sum it), else the original text."""
    text = str(raw or "").replace(",", "").strip()
    return float(text) if _NUMBER_RE.match(text) else str(raw or "")


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


def transactions_to_xlsx(transactions: list[dict[str, Any]], include_categories: bool = True) -> bytes:
    """Return .xlsx bytes: bold frozen header, numeric amounts, sized columns, autofilter."""
    fields = export_fields(include_categories)
    out, wb, ws, header, money = _new_workbook("Transactions")

    for col, field in enumerate(fields):
        ws.write_string(0, col, _HEADERS[field], header)
        ws.set_column(col, col, _WIDTHS[field])

    for row, tx in enumerate(transactions, start=1):
        for col, field in enumerate(fields):
            value = _amount_value(tx.get(field)) if field == "amount" else str(tx.get(field) or "")
            if isinstance(value, float):
                ws.write_number(row, col, value, money)
            elif value:
                ws.write_string(row, col, value)

    ws.freeze_panes(1, 0)
    ws.autofilter(0, 0, max(len(transactions), 1), len(fields) - 1)
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
