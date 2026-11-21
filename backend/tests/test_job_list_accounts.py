"""GET /api/jobs adds each job's reconciliation status and the user's accounts."""
from unittest.mock import patch

from services.balances import fill_running_balances


def _rows(opening):
    """+20 then -10 from `opening`."""
    return fill_running_balances([
        {"date": "1", "description": "a", "amount": "20.00", "type": "credit", "category": "Income",
         "balance": f"{opening + 20:.2f}"},
        {"date": "2", "description": "b", "amount": "10.00", "type": "debit", "category": "Other",
         "balance": f"{opening + 10:.2f}"},
    ])


def _job(job_id, start, end, opening, closing, payload=True):
    return {
        "id": job_id, "created_at": "2026-11-20T00:00:00", "transaction_count": 2, "currency": "USD",
        "has_payload": payload, "conversion_mode": "fast",
        "transactions": _rows(opening) if payload else [],
        "statement_meta": {"account_last4": "1234", "account_type": "checking", "bank_name": "Chase",
                           "period_start": start, "period_end": end, "opening_balance": opening,
                           "closing_balance": closing, "total_credits": 20.0, "total_debits": 10.0,
                           "account_count": 1} if payload else None,
    }


def test_job_list_has_statuses_and_accounts(client):
    jobs = [
        _job("feb", "2026-02-01", "2026-02-28", 110.0, 120.0),
        _job("jan", "2026-01-01", "2026-01-31", 100.0, 110.0),
        _job("gone", None, None, None, None, payload=False),
    ]
    with patch("main.list_jobs", return_value=(jobs, None)):
        body = client.get("/api/jobs").json()
    statuses = {j["id"]: j["reconciliation_status"] for j in body["jobs"]}
    assert statuses == {"feb": "reconciled", "jan": "reconciled", "gone": None}
    assert body["jobs"][0]["account_last4"] == "1234" and body["jobs"][0]["period_end"] == "2026-02-28"
    # Saved rows and the raw summary never leave the server in the list.
    assert "transactions" not in body["jobs"][0] and "statement_meta" not in body["jobs"][0]
    [account] = body["accounts"]
    assert [s["job_id"] for s in account["statements"]] == ["jan", "feb"]
    assert account["links"][0]["kind"] == "ok"
    assert body["unmatched_job_ids"] == []
