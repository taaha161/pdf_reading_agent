"""Tests for statement reconciliation (balance chain, hints, status)."""
from services.balances import balance_breaks, fill_running_balances, printed_balances
from services.reconciliation import MISMATCH, RECONCILED, UNVERIFIED, reconcile


def _scan(spec):
    """Rows as a scan stores them. spec: (type, amount, printed balance or "")."""
    rows = [{"type": t, "amount": a, "balance": b, "description": f"row {i}"} for i, (t, a, b) in enumerate(spec)]
    return fill_running_balances(rows)


# Bank account, oldest first, opening 1000.
GOOD = [
    ("credit", "500.00", "1500.00"),
    ("debit", "200.00", ""),
    ("debit", "50.00", "1250.00"),
    ("credit", "100.00", "1350.00"),
    ("debit", "30.00", "1320.00"),
]


def test_fill_marks_printed_balances():
    rows = _scan(GOOD)
    assert [r["balance_printed"] for r in rows] == [True, False, True, True, True]
    assert printed_balances(rows) == {0: 1500.0, 2: 1250.0, 3: 1350.0, 4: 1320.0}


def test_legacy_rows_have_no_printed_marker():
    rows = [{"type": "debit", "amount": "5", "balance": "10.00"}]
    assert printed_balances(rows) is None
    result = reconcile(rows)
    assert result["status"] == UNVERIFIED and "Scan the statement again" in result["reason"]


def test_reconciled_statement():
    result = reconcile(_scan(GOOD))
    assert result["status"] == RECONCILED
    assert result["opening_balance"] == 1000.0 and result["closing_balance"] == 1320.0
    assert result["total_credits"] == 600.0 and result["total_debits"] == 280.0
    [check] = result["checks"]
    assert check["key"] == "balance_chain" and check["status"] == "pass" and check["difference"] == 0.0
    assert result["hints"] == []


def test_missing_row_is_located():
    # A 75.00 debit between rows 2 and 3 was never extracted: 1250 + 100 - 75 = 1275.
    spec = list(GOOD)
    spec[3] = ("credit", "100.00", "1275.00")
    spec[4] = ("debit", "30.00", "1245.00")
    result = reconcile(_scan(spec))
    assert result["status"] == MISMATCH
    assert result["checks"][0]["breaks"] == 1
    assert result["checks"][0]["difference"] == -75.0
    assert result["hints"] == [{"kind": "missing_row", "from_row": 2, "to_row": 3, "amount": 75.0, "direction": "debit"}]


def test_flipped_type_is_pinned_to_its_row():
    spec = list(GOOD)
    spec[3] = ("debit", "100.00", "1350.00")  # really a credit
    result = reconcile(_scan(spec))
    assert result["status"] == MISMATCH
    assert result["hints"] == [{"kind": "flipped_type", "row_index": 3, "amount": 100.0}]


def test_duplicate_row_is_pinned_to_its_row():
    # Row 2 (debit 50) is read again after its printed balance; the copy breaks the next step.
    spec = GOOD[:3] + [("debit", "50.00", "")] + GOOD[3:]
    result = reconcile(_scan(spec))
    assert result["status"] == MISMATCH
    assert result["hints"] == [{"kind": "duplicate_row", "row_index": 3, "amount": 50.0}]


def test_identical_twins_point_at_the_later_copy():
    rows = [
        {"date": "03/01", "description": "Opening", "type": "credit", "amount": "100.00", "balance": "100.00"},
        {"date": "03/02", "description": "COFFEE", "type": "debit", "amount": "10.00", "balance": ""},
        {"date": "03/02", "description": "COFFEE", "type": "debit", "amount": "10.00", "balance": "90.00"},
    ]
    result = reconcile(fill_running_balances(rows))
    assert result["hints"] == [{"kind": "duplicate_row", "row_index": 2, "amount": 10.0}]


def test_ambiguous_gap_gets_no_hint():
    # Two equal debits between the printed balances: either could be the duplicate.
    rows = _scan([
        ("credit", "100.00", "100.00"),
        ("debit", "10.00", ""),
        ("debit", "10.00", "90.00"),
    ])
    result = reconcile(rows)
    assert result["status"] == MISMATCH and result["hints"] == []


def test_newest_first_statement_hint_uses_display_order():
    # Same as GOOD reversed (newest row on top), with row "credit 100" read as a debit.
    spec = list(reversed(GOOD))
    spec[1] = ("debit", "100.00", "1350.00")
    rows = _scan(spec)
    (newest_first, _), _ = balance_breaks(rows, printed_balances(rows))
    assert newest_first
    result = reconcile(rows)
    assert result["status"] == MISMATCH
    assert result["hints"] == [{"kind": "flipped_type", "row_index": 1, "amount": 100.0}]


def test_credit_card_sign():
    # Balance is what's owed: purchases raise it, payments lower it.
    good = [("debit", "40.00", "140.00"), ("debit", "10.00", "150.00"), ("credit", "100.00", "50.00")]
    assert reconcile(_scan(good))["status"] == RECONCILED

    missed = [("debit", "40.00", "140.00"), ("debit", "10.00", "175.00"), ("credit", "100.00", "75.00")]
    result = reconcile(_scan(missed))
    assert result["status"] == MISMATCH
    # 140 + 10 = 150 expected, 175 printed: a 25.00 purchase (debit) is missing.
    assert result["hints"] == [{"kind": "missing_row", "from_row": 0, "to_row": 1, "amount": 25.0, "direction": "debit"}]


def test_user_edit_fixes_mismatch():
    spec = list(GOOD)
    spec[3] = ("debit", "100.00", "1350.00")
    rows = _scan(spec)
    assert reconcile(rows)["status"] == MISMATCH
    rows[3]["type"] = "credit"  # the user corrects the row
    assert reconcile(rows)["status"] == RECONCILED


def test_unverified_without_balances():
    result = reconcile(_scan([("debit", "10.00", ""), ("credit", "5.00", "")]))
    assert result["status"] == UNVERIFIED and "doesn't print running balances" in result["reason"]
    assert result["checks"] == []


def test_unverified_with_one_balance():
    result = reconcile(_scan([("debit", "10.00", ""), ("credit", "5.00", "95.00")]))
    assert result["status"] == UNVERIFIED and "only one balance" in result["reason"]


def test_no_rows():
    assert reconcile([])["status"] == UNVERIFIED


# --- Printed summary box -------------------------------------------------------------------

def _meta(opening=1000.0, credits=600.0, debits=280.0, closing=1320.0, account_type="checking", **extra):
    return {"opening_balance": opening, "total_credits": credits, "total_debits": debits,
            "closing_balance": closing, "account_type": account_type, "account_count": 1, **extra}


def _checks(result):
    return {c["key"]: c["status"] for c in result["checks"]}


def test_summary_matches_rows():
    result = reconcile(_scan(GOOD), _meta())
    assert result["status"] == RECONCILED
    assert _checks(result) == {"balance_chain": "pass", "opening": "pass", "credits": "pass", "debits": "pass", "closing": "pass"}


def test_summary_works_without_running_balances():
    rows = _scan([(t, a, "") for t, a, _ in GOOD])
    result = reconcile(rows, _meta())
    assert result["status"] == RECONCILED
    assert _checks(result) == {"opening": "skipped", "credits": "pass", "debits": "pass", "closing": "pass"}
    assert result["opening_balance"] == 1000.0 and result["closing_balance"] == 1320.0


def test_summary_catches_a_missed_row_without_running_balances():
    rows = _scan([(t, a, "") for t, a, _ in GOOD[:-1]])  # the 30.00 debit was missed
    result = reconcile(rows, _meta())
    assert result["status"] == MISMATCH
    debits = next(c for c in result["checks"] if c["key"] == "debits")
    assert debits == {"key": "debits", "status": "fail", "expected": 280.0, "actual": 250.0, "difference": 30.0}
    closing = next(c for c in result["checks"] if c["key"] == "closing")
    assert closing["status"] == "fail" and closing["difference"] == -30.0


def test_misread_summary_is_skipped_not_blamed_on_rows():
    # 1000 + 600 - 280 != 9999: the summary itself doesn't add up, so it was misread.
    result = reconcile(_scan(GOOD), _meta(closing=9999.0))
    assert result["status"] == RECONCILED  # the running balances still check out
    assert all(c["status"] == "skipped" for c in result["checks"] if c["key"] != "balance_chain")


def test_credit_card_summary():
    rows = _scan([("debit", "40.00", ""), ("debit", "10.00", ""), ("credit", "100.00", "")])
    meta = _meta(opening=100.0, credits=100.0, debits=50.0, closing=50.0, account_type="credit_card")
    assert reconcile(rows, meta)["status"] == RECONCILED


def test_card_sign_from_summary_math_when_type_unknown():
    rows = _scan([("debit", "40.00", ""), ("debit", "10.00", ""), ("credit", "100.00", "")])
    meta = _meta(opening=100.0, credits=100.0, debits=50.0, closing=50.0, account_type="other")
    assert reconcile(rows, meta)["status"] == RECONCILED


def test_account_type_settles_sign_for_two_balances():
    # With two printed balances, a flipped debit also fits the credit-card reading; knowing it's a
    # checking account rules that out.
    rows = _scan([("credit", "500.00", "1500.00"), ("debit", "100.00", "1600.00")])
    assert reconcile(rows)["status"] == RECONCILED  # ambiguous on its own
    result = reconcile(rows, {"account_type": "checking", "account_count": 1})
    assert result["status"] == MISMATCH
    assert result["hints"] == [{"kind": "flipped_type", "row_index": 1, "amount": 100.0}]


def test_multi_account_statement_is_unverified():
    result = reconcile(_scan(GOOD), _meta(account_count=2))
    assert result["status"] == UNVERIFIED and "more than one account" in result["reason"]


def test_meta_with_no_amounts_falls_back_to_chain():
    meta = _meta(opening=None, credits=None, debits=None, closing=None)
    assert _checks(reconcile(_scan(GOOD), meta)) == {"balance_chain": "pass"}
