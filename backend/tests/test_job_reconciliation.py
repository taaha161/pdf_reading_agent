"""GET/PATCH /api/jobs/{id} return a reconciliation recomputed from the saved rows."""
import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from main import app, get_current_user

JOB_ID = str(uuid.uuid4())


def _row(type_, amount, balance, printed=True):
    return {"date": "03/01", "description": "x", "amount": amount, "type": type_, "category": "Other",
            "balance": balance, "balance_printed": printed}


# Row 2 is really a credit, so the printed balances don't add up.
ROWS = [
    _row("credit", "500.00", "1500.00"),
    _row("debit", "200.00", "1300.00"),
    _row("debit", "100.00", "1400.00"),
    _row("debit", "50.00", "1350.00"),
]


@pytest.fixture
def client():
    app.dependency_overrides[get_current_user] = lambda: "user-1"
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_current_user, None)


def test_job_detail_has_reconciliation(client):
    job = {"transactions": ROWS, "currency": "USD"}
    with patch("main.get_job", return_value=job):
        rec = client.get(f"/api/jobs/{JOB_ID}").json()["reconciliation"]
    assert rec["status"] == "mismatch"
    assert rec["hints"] == [{"kind": "flipped_type", "row_index": 2, "amount": 100.0,
                             "from_row": None, "to_row": None, "direction": None}]


def test_patch_recomputes_reconciliation(client):
    fixed = [dict(r) for r in ROWS]
    fixed[2]["type"] = "credit"
    with patch("main.get_job", side_effect=[{"transactions": ROWS}, {"transactions": fixed}]), patch(
        "main.update_job_transactions"
    ) as update:
        r = client.patch(f"/api/jobs/{JOB_ID}", json={"transactions": fixed})
    assert r.json()["reconciliation"]["status"] == "reconciled"
    # The printed-balance marker survives the round trip through the Transaction model.
    assert update.call_args.args[2][2]["balance_printed"] is True


def test_purged_job_has_no_reconciliation(client):
    with patch("main.get_job", return_value={"transactions": [], "data_status": "purged"}):
        assert client.get(f"/api/jobs/{JOB_ID}").json()["reconciliation"] is None
