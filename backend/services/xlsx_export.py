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
    GROUP_FIELD,
    GROUP_TOTALS_HEADER,
    NET_TOTAL,
    NO_CATEGORY,
    NO_GROUP,
    TOTALS_HEADER,
    amount_value,
    category_totals,
    export_fields,
    export_totals,
    group_totals,
    has_groups,
)

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

_HEADERS = {
    "date": "Date", "description": "Description", "amount": "Amount", "type": "Type", "category": "Category",
    GROUP_FIELD: "Sub-category",
}
_WIDTHS = {"date": 12, "description": 48, "amount": 14, "type": 10, "category": 20, GROUP_FIELD: 20}
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
    With a group ("Sub-category") column, the category table has no "All categories" row and a second
    table follows (after one blank row): one row per sub-category, then "Net total".

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
    money = wb.add_format({"num_format": _MONEY_FORMAT})
    bold = wb.add_format({"bold": True, "top": 1})
    bold_money = wb.add_format({"bold": True, "top": 1, "num_format": _MONEY_FORMAT})
    count, credit, debit = export_totals(transactions)

    def table(top: int, head: tuple, field: str, rows: list, blank: str, total_label: str | None) -> int:
        """Write one totals table with its header at 0-based row `top`; return its last row's index.
        total_label None leaves out the overall total row."""
        for col, label in enumerate(head):
            ws.write_string(top, col, label, header)
        for i, (name, n, money_in, money_out) in enumerate(rows):
            r = top + 1 + i  # 0-based; Excel row is r + 1
            match = f'--({rng(field)}="")' if name == blank else f"--({rng(field)}=A{r + 1})"
            ws.write_string(r, 0, name)
            ws.write_formula(r, 1, f"=SUMPRODUCT({match})", None, n)
            ws.write_formula(r, 2, f'=SUMPRODUCT({match},--({types}="credit"),{amounts})', money, money_in)
            ws.write_formula(r, 3, f'=SUMPRODUCT({match},--({types}="debit"),{amounts})', money, money_out)
            ws.write_formula(r, 4, f"=C{r + 1}-D{r + 1}", money, round(money_in - money_out, 2))
        r = top + 1 + len(rows)  # the overall total row
        if total_label is None:
            return r - 1
        ws.write_string(r, 0, total_label, bold)
        ws.write_formula(r, 1, f"=COUNTA({types})", bold, count)
        ws.write_formula(r, 2, f'=SUMPRODUCT(--({types}="credit"),{amounts})', bold_money, credit)
        ws.write_formula(r, 3, f'=SUMPRODUCT(--({types}="debit"),{amounts})', bold_money, debit)
        ws.write_formula(r, 4, f"=C{r + 1}-D{r + 1}", bold_money, round(credit - debit, 2))
        return r

    groups = category_totals(transactions) if "category" in fields else []
    # Header at row `last + 1` (0-based); row `last` is the blank spacer.
    grouped = GROUP_FIELD in fields
    # Grouped files end in "Net total" instead, so the same figure isn't shown twice.
    all_label = None if grouped and groups else ALL_CATEGORIES
    end = table(last + 1, TOTALS_HEADER, "category", groups, NO_CATEGORY, all_label)
    labels = [ALL_CATEGORIES] + [g[0] for g in groups]
    if grouped:
        by_group = group_totals(transactions)
        table(end + 2, GROUP_TOTALS_HEADER, GROUP_FIELD, by_group, NO_GROUP, NET_TOTAL)
        labels += [g[0] for g in by_group]

    # Column A holds dates above and category/group names here; widen it to fit both (capped).
    longest = max(len(x) for x in labels)
    ws.set_column(0, 0, max(_WIDTHS["date"], min(longest + 2, 32)))
    ws.set_column(3, 3, max(_WIDTHS["type"], 14))  # money out lands in the narrow Type column


def transactions_to_xlsx(
    transactions: list[dict[str, Any]], include_categories: bool = True, include_totals: bool = False
) -> bytes:
    """Return .xlsx bytes: bold frozen header, numeric amounts, sized columns, autofilter.

    include_totals adds a per-category totals table and an "All categories" row under the rows
    (off by default: accounting imports expect rows only).
    """
    fields = export_fields(include_categories, has_groups(transactions))
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
