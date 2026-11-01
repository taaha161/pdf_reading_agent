"""Tests for /api/feedback (optional post-scan feedback prompt)."""
from unittest.mock import patch

import pytest

JOB_ID = "00000000-0000-0000-0000-000000000042"


@pytest.fixture
def deps():
    with patch("main.record_feedback") as record, patch("main.notify_feedback") as notify:
        yield {"record": record, "notify": notify}


def test_records_rating_and_comment(client, deps):
    r = client.post("/api/feedback", json={"job_id": JOB_ID, "rating": 4, "comment": "  Missed one row ", "contact_ok": True})
    assert r.status_code == 200
    assert deps["record"].call_args.args[:5] == ("test-user-id", JOB_ID, 4, "Missed one row", True)
    deps["notify"].assert_called_once()


def test_rating_only_is_enough(client, deps):
    assert client.post("/api/feedback", json={"rating": 5}).status_code == 200
    assert deps["record"].call_args.args[1:4] == (None, 5, None)


def test_empty_feedback_rejected(client, deps):
    assert client.post("/api/feedback", json={"comment": "   "}).status_code == 400
    deps["record"].assert_not_called()


def test_rating_out_of_range_rejected(client, deps):
    assert client.post("/api/feedback", json={"rating": 6}).status_code == 422


def test_storage_failure_still_returns_ok(client, deps):
    deps["record"].side_effect = RuntimeError("db down")
    assert client.post("/api/feedback", json={"rating": 2}).status_code == 200
