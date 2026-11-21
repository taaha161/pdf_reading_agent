"""Tests for linking a user's saved statements of the same account month to month."""
from services.reconciliation import account_continuity


def _job(job_id, start, end, opening, closing, last4="1234", currency="USD", account_type="checking", status="reconciled", bank="Chase"):
    return {
        "id": job_id,
        "currency": currency,
        "statement_meta": {"account_last4": last4, "account_type": account_type, "bank_name": bank,
                           "period_start": start, "period_end": end},
        "reconciliation": {"status": status, "opening_balance": opening, "closing_balance": closing},
    }


def _kinds(account):
    return [link["kind"] for link in account["links"]]


def test_months_that_chain():
    jobs = [
        _job("feb", "2026-02-01", "2026-02-28", 120.0, 150.0),
        _job("jan", "2026-01-01", "2026-01-31", 100.0, 120.0),
    ]
    [account], unmatched = account_continuity(jobs)
    assert unmatched == []
    assert [s["job_id"] for s in account["statements"]] == ["jan", "feb"]  # oldest first
    assert _kinds(account) == ["ok"]
    assert account["bank_name"] == "Chase" and account["account_type"] == "bank"


def test_cycle_drift_within_a_week_is_fine():
    jobs = [_job("a", "2026-01-05", "2026-02-04", 0.0, 10.0), _job("b", "2026-02-09", "2026-03-06", 10.0, 20.0)]
    assert _kinds(account_continuity(jobs)[0][0]) == ["ok"]


def test_missing_month_is_a_gap():
    jobs = [_job("jan", "2026-01-01", "2026-01-31", 100.0, 120.0), _job("mar", "2026-03-01", "2026-03-31", 130.0, 140.0)]
    [link] = account_continuity(jobs)[0][0]["links"]
    assert link == {"from_job": "jan", "to_job": "mar", "kind": "gap",
                    "missing_from": "2026-02-01", "missing_to": "2026-02-28"}


def test_gap_without_start_dates_assumes_monthly_cycle():
    jobs = [_job("jan", None, "2026-01-31", 1.0, 2.0), _job("mar", None, "2026-03-31", 2.0, 3.0)]
    assert _kinds(account_continuity(jobs)[0][0]) == ["gap"]


def test_balances_that_dont_connect():
    jobs = [_job("jan", "2026-01-01", "2026-01-31", 100.0, 120.0), _job("feb", "2026-02-01", "2026-02-28", 170.0, 200.0)]
    [link] = account_continuity(jobs)[0][0]["links"]
    assert link["kind"] == "balance_mismatch" and link["difference"] == 50.0


def test_unknown_balances_dont_flag_a_mismatch():
    jobs = [_job("jan", "2026-01-01", "2026-01-31", None, None), _job("feb", "2026-02-01", "2026-02-28", 170.0, 200.0)]
    assert _kinds(account_continuity(jobs)[0][0]) == ["ok"]


def test_same_period_twice_is_a_duplicate():
    jobs = [_job("a", "2026-01-01", "2026-01-31", 1.0, 2.0), _job("b", "2026-01-01", "2026-01-31", 1.0, 2.0)]
    assert _kinds(account_continuity(jobs)[0][0]) == ["duplicate"]


def test_accounts_are_split_by_number_currency_and_kind():
    jobs = [
        _job("chk", "2026-01-01", "2026-01-31", 1.0, 2.0),
        _job("card", "2026-01-01", "2026-01-31", 1.0, 2.0, account_type="credit_card"),
        _job("eur", "2026-01-01", "2026-01-31", 1.0, 2.0, currency="EUR"),
        _job("other", "2026-01-01", "2026-01-31", 1.0, 2.0, last4="9999"),
        _job("chk2", "2026-02-01", "2026-02-28", 2.0, 3.0, bank="JPMorgan Chase Bank, N.A."),
    ]
    accounts, _ = account_continuity(jobs)
    assert len(accounts) == 4
    chk = next(a for a in accounts if len(a["statements"]) == 2)
    assert chk["bank_name"] == "JPMorgan Chase Bank, N.A."  # most recent name wins
    assert accounts[0] is chk  # most recently active account first


def test_unplaceable_statements_are_unmatched():
    no_meta = {"id": "x", "currency": "USD", "statement_meta": None, "reconciliation": None}
    no_number = _job("y", "2026-01-01", "2026-01-31", 1.0, 2.0, last4=None)
    no_period = _job("z", None, None, 1.0, 2.0)
    accounts, unmatched = account_continuity([no_meta, no_number, no_period])
    assert accounts == [] and unmatched == ["x", "y", "z"]
