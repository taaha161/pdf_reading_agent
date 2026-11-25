"""Turn list of transaction dicts into an Excel (.xlsx) workbook.

Written with XlsxWriter, which stores text in a shared-strings table the way Excel does.
openpyxl 3.1 writes inline strings instead; that is valid, but many phone viewers
(e.g. Android file/document previewers) ignore them and show only the number cells.
"""
import io
import re
from typing import Any

import xlsxwriter
from xlsxwriter.utility import xl_col_to_name

from services.csv_export import (
    ALL_CATEGORIES,
    BALANCE,
    CREDIT,
    DEBIT,
    GROUP_FIELD,
    GROUP_TOTALS_HEADER,
    NET_TOTAL,
    NO_CATEGORY,
    NO_GROUP,
    TOTALS_HEADER,
    category_totals,
    export_fields,
    export_totals,
    group_totals,
    has_balances,
    has_groups,
    STATEMENT_FIELD,
    bulk_fields,
    bulk_rows,
    statement_row,
    with_balance_rows,
)

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

_HEADERS = {
    "date": "Date", "description": "Description", DEBIT: "Debit", CREDIT: "Credit", BALANCE: "Balance",
    "category": "Category", GROUP_FIELD: "Sub-category", STATEMENT_FIELD: "Statement",
}
_WIDTHS = {
    "date": 12, "description": 48, DEBIT: 14, CREDIT: 14, BALANCE: 14, "category": 20, GROUP_FIELD: 20,
    STATEMENT_FIELD: 28,
}
_MONEY_FIELDS = (DEBIT, CREDIT, BALANCE)
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
    amounts count as 0. Money in sums the Credit column, money out the Debit column.
    """
    first, last = 2, len(transactions) + 1  # Excel row numbers of the data

    def rng(field: str) -> str:
        col = xl_col_to_name(fields.index(field))
        return f"{col}{first}:{col}{last}"

    credits, debits, dates = rng(CREDIT), rng(DEBIT), rng("date")
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
            ws.write_formula(r, 2, f"=SUMPRODUCT({match},{credits})", money, money_in)
            ws.write_formula(r, 3, f"=SUMPRODUCT({match},{debits})", money, money_out)
            ws.write_formula(r, 4, f"=C{r + 1}-D{r + 1}", money, round(money_in - money_out, 2))
        r = top + 1 + len(rows)  # the overall total row
        if total_label is None:
            return r - 1
        ws.write_string(r, 0, total_label, bold)
        ws.write_formula(r, 1, f"=ROWS({dates})", bold, count)
        ws.write_formula(r, 2, f"=SUM({credits})", bold_money, credit)
        ws.write_formula(r, 3, f"=SUM({debits})", bold_money, debit)
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


_CHECK_LABELS = {
    "balance_chain": "Running balances",
    "opening": "Opening balance",
    "credits": "Total money in",
    "debits": "Total money out",
    "closing": "Closing balance",
}
_STATUS_LABELS = {
    "reconciled": "Reconciles with the statement",
    "mismatch": "Doesn't add up",
    "unverified": "Can't check this statement",
}
_RESULT_LABELS = {"pass": "Matches", "fail": "Doesn't match", "skipped": "Not checked"}


def _hint_line(hint: dict[str, Any]) -> str:
    amount = f"{hint.get('amount', 0):,.2f}"
    if hint.get("kind") == "flipped_type" and hint.get("row_index") is not None:
        return f"Row {hint['row_index'] + 1} ({amount}) may have the wrong direction (credit vs debit)."
    if hint.get("kind") == "duplicate_row" and hint.get("row_index") is not None:
        return f"Row {hint['row_index'] + 1} ({amount}) may have been read twice."
    if hint.get("kind") == "missing_row" and hint.get("from_row") is not None and hint.get("to_row") is not None:
        what = "credit" if hint.get("direction") == "credit" else "debit"
        return f"A {what} of {amount} may be missing between rows {hint['from_row'] + 1} and {hint['to_row'] + 1}."
    return ""


def _write_reconciliation(wb, header, money, reconciliation: dict[str, Any], fields: list[str], data_rows: int) -> None:
    """A "Reconciliation" sheet: what the statement prints vs what the rows add up to.

    Money in/out are live SUMs over the Transactions sheet's Credit/Debit columns (with cached
    values), so a correction made in Excel shows up here. The statement's own figures are values.
    Row numbers refer to the transaction rows as listed in the app.
    """
    ws = wb.add_worksheet("Reconciliation")
    bold = wb.add_format({"bold": True})
    ws.set_column(0, 0, 22)
    ws.set_column(1, 3, 18)
    ws.set_column(4, 4, 16)
    ws.write_string(0, 0, _STATUS_LABELS.get(reconciliation.get("status"), ""), bold)
    if reconciliation.get("reason"):
        ws.write_string(1, 0, reconciliation["reason"])
    head = ("Check", "Statement says", "We extracted", "Difference", "Result")
    for col, label in enumerate(head):
        ws.write_string(3, col, label, header)
    last = data_rows + 1  # Excel row of the last data row on the Transactions sheet
    sums = {
        key: f"=SUM(Transactions!{xl_col_to_name(fields.index(field))}2:{xl_col_to_name(fields.index(field))}{last})"
        for key, field in (("credits", CREDIT), ("debits", DEBIT))
    }
    r = 4
    for check in reconciliation.get("checks") or []:
        key = check.get("key")
        expected, actual = check.get("expected"), check.get("actual")
        ws.write_string(r, 0, _CHECK_LABELS.get(key, str(key)))
        if expected is not None:
            ws.write_number(r, 1, expected, money)
        if actual is not None:
            if key in sums and data_rows:
                ws.write_formula(r, 2, sums[key], money, actual)
            else:
                ws.write_number(r, 2, actual, money)
        if expected is not None and actual is not None:
            ws.write_formula(r, 3, f"=B{r + 1}-C{r + 1}", money, check.get("difference") or 0)
        ws.write_string(r, 4, _RESULT_LABELS.get(check.get("status"), ""))
        r += 1
    hints = [line for line in (_hint_line(h) for h in reconciliation.get("hints") or []) if line]
    if hints:
        ws.write_string(r + 1, 0, "Where to look", bold)
        for i, line in enumerate(hints):
            ws.write_string(r + 2 + i, 0, line)


def transactions_to_xlsx(
    transactions: list[dict[str, Any]],
    include_categories: bool = True,
    include_totals: bool = False,
    reconciliation: dict[str, Any] | None = None,
) -> bytes:
    """Return .xlsx bytes laid out like a statement: Date, Description, Debit, Credit[, Balance],
    Category[, Sub-category], with a bold frozen header, numeric money cells, sized columns and an autofilter.

    include_totals adds a per-category totals table and an "All categories" row under the rows
    (off by default: accounting imports expect rows only).
    Without totals, statements whose balances chain get "Opening balance" / "Closing balance" rows
    around the transactions (see with_balance_rows).
    reconciliation (schemas.Reconciliation) adds a second "Reconciliation" sheet; the first sheet
    stays rows-only so accounting imports are unaffected.
    """
    fields = export_fields(include_categories, has_groups(transactions), has_balances(transactions))
    out, wb, ws, header, money = _new_workbook("Transactions")

    rows = [statement_row(t) for t in transactions]
    if not include_totals:  # the totals formulas cover the data rows, so they keep transactions only
        rows = with_balance_rows(rows, transactions)
    _write_rows(ws, fields, rows, header, money)
    if include_totals and transactions:
        _write_totals(wb, ws, transactions, fields, header)
    if reconciliation:
        _write_reconciliation(wb, header, money, reconciliation, fields, len(rows))
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


def _write_rows(ws, fields: list[str], rows: list[dict[str, Any]], header, money) -> None:
    """Header row + one row per dict: numeric money cells, sized columns, frozen header, autofilter."""
    for col, field in enumerate(fields):
        ws.write_string(0, col, _HEADERS[field], header)
        ws.set_column(col, col, _WIDTHS[field])
    for row, cells in enumerate(rows, start=1):
        for col, field in enumerate(fields):
            value = cells.get(field) if field in _MONEY_FIELDS else str(cells.get(field) or "")
            if isinstance(value, float):
                ws.write_number(row, col, value, money)
            elif value:
                ws.write_string(row, col, value)
    ws.freeze_panes(1, 0)
    ws.autofilter(0, 0, max(len(rows), 1), len(fields) - 1)


_SHEET_NAME_BAD = re.compile(r"[\[\]:*?/\\]")


def _sheet_names(names: list[str]) -> list[str]:
    """Valid, unique Excel sheet names (max 31 chars, no []:*?/\\, not "All statements") for each statement."""
    taken = {ALL_STATEMENTS_SHEET.lower()}
    out = []
    for name in names:
        base = re.sub(r"\.pdf$", "", name, flags=re.I)
        base = _SHEET_NAME_BAD.sub(" ", base).strip().strip("'") or "Statement"
        candidate, n = base[:31], 2
        while candidate.lower() in taken:
            suffix = f" ({n})"
            candidate, n = base[: 31 - len(suffix)] + suffix, n + 1
        taken.add(candidate.lower())
        out.append(candidate)
    return out


ALL_STATEMENTS_SHEET = "All statements"


def bulk_to_xlsx(statements: list[tuple[str, list[dict[str, Any]]]], include_categories: bool = True) -> bytes:
    """One workbook for a bulk upload: an "All statements" sheet with every row and a Statement column
    naming its source file, then one sheet per statement laid out like a single download."""
    out, wb, ws, header, money = _new_workbook(ALL_STATEMENTS_SHEET)
    _write_rows(ws, bulk_fields(statements, include_categories), bulk_rows(statements), header, money)
    for sheet_name, (_, transactions) in zip(_sheet_names([n for n, _ in statements]), statements):
        sheet = wb.add_worksheet(sheet_name)
        fields = export_fields(include_categories, False, has_balances(transactions))
        rows = with_balance_rows([statement_row(t) for t in transactions], transactions)
        _write_rows(sheet, fields, rows, header, money)
    wb.close()
    return out.getvalue()
