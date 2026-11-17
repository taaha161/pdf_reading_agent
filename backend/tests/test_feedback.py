"""Tests for /api/feedback (optional post-scan feedback prompt)."""
from unittest.mock import patch

import pytest

JOB_ID = "00000000-0000-0000-0000-000000000042"


@pytest.fixture
def deps():
    with patch("main.record_feedback") as record, patch("main.notify_feedback") as notify, patch(
        "main.get_auth_user", return_value={"email": "ted@example.com", "full_name": "Ted"}
    ) as auth_user, patch("main.get_job_owner", return_value="owner-id") as job_owner:
        yield {"record": record, "notify": notify, "auth_user": auth_user, "job_owner": job_owner}


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


def test_notification_includes_logged_in_email(client, deps):
    client.post("/api/feedback", json={"job_id": JOB_ID, "rating": 5})
    kw = deps["notify"].call_args.kwargs
    assert kw["email"] == "ted@example.com" and kw["job_id"] == JOB_ID and kw["via_job_link"] is False
    deps["job_owner"].assert_not_called()


def test_anonymous_feedback_matched_via_job_owner(client, deps):
    from main import app
    from auth import get_current_user_optional

    prev = app.dependency_overrides.get(get_current_user_optional)
    app.dependency_overrides[get_current_user_optional] = lambda: None
    try:
        client.post("/api/feedback", json={"job_id": JOB_ID, "rating": 3})
    finally:
        app.dependency_overrides[get_current_user_optional] = prev
    deps["job_owner"].assert_called_once_with(JOB_ID)
    deps["auth_user"].assert_called_once_with(user_id="owner-id")
    assert deps["notify"].call_args.args[2] == "owner-id"
    assert deps["notify"].call_args.kwargs["via_job_link"] is True


def test_notify_feedback_sets_reply_to_customer():
    from services import notifications

    with patch.object(notifications, "_send") as send, patch.object(notifications.threading, "Thread") as thread:
        thread.side_effect = lambda target, args, daemon: type("T", (), {"start": lambda self: target(*args)})()
        notifications.notify_feedback(4, "nice", "u1", True, email="ted@example.com", job_id=JOB_ID)
    subject, text, reply_to = send.call_args.args
    assert subject == "Feedback 4/5 from ted@example.com"
    assert reply_to == "ted@example.com" and JOB_ID in text
