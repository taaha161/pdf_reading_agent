"""Tiered upload size limit: anonymous < signed in < subscribed."""
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

import main
from main import app, get_current_user_optional

PDF_30 = b"%PDF-1.4\n" + b"0" * 21  # 30 bytes
LIMITS = {"MAX_FILE_SIZE": 20, "MAX_FILE_SIZE_SIGNED_IN": 30, "MAX_FILE_SIZE_PAID": 50}


@pytest.fixture
def client():
    main.limiter.reset()
    with patch.multiple(main, **LIMITS), patch("main.verify_recaptcha", AsyncMock(return_value=True)), patch(
        "main.count_trial_runs_by_ip", return_value=0
    ), patch("main.limiter.enabled", False):
        with TestClient(app) as c:
            yield c
    app.dependency_overrides.pop(get_current_user_optional, None)


def _as(user_id):
    app.dependency_overrides[get_current_user_optional] = lambda: user_id


def _scan(client, content):
    return client.post(
        "/api/scans",
        files={"file": ("big.pdf", content, "application/pdf")},
        data={"recaptcha_token": "tok"},
    )


def test_anonymous_over_limit_is_told_to_sign_up(client, caplog):
    _as(None)
    r = _scan(client, PDF_30)
    assert r.status_code == 413
    detail = r.json()["detail"]
    assert detail["code"] == "FILE_TOO_LARGE"
    assert detail["upgrade"] == "signup"
    assert (detail["size_bytes"], detail["max_bytes"]) == (30, 20)
    assert "size=30 bytes" in caplog.text and "tier=anonymous" in caplog.text


def test_signed_in_gets_higher_limit_then_told_to_subscribe(client):
    _as("user-1")
    with patch("main.get_billing", return_value={"balance_cents": 0}):
        r = _scan(client, PDF_30 + b"0")  # 31 > 30
    assert r.status_code == 413
    assert r.json()["detail"]["upgrade"] == "subscribe"
    assert r.json()["detail"]["max_bytes"] == 30


def test_subscriber_limit_has_no_upgrade(client):
    _as("user-1")
    with patch("main.get_billing", return_value={"balance_cents": 1000, "stripe_subscription_id": "sub_1"}):
        r = _scan(client, PDF_30 + b"0" * 21)  # 51 > 50
    assert r.status_code == 413
    assert r.json()["detail"]["upgrade"] is None
    assert r.json()["detail"]["max_bytes"] == 50


@pytest.mark.parametrize(
    "user_id,billing,expected",
    [(None, None, 20), ("u", None, 30), ("u", {"balance_cents": 0, "stripe_subscription_id": "sub_1"}, 50)],
)
def test_usage_reports_max_file_bytes(client, user_id, billing, expected):
    _as(user_id)
    with patch("main.get_billing", return_value=billing):
        assert client.get("/api/usage").json()["max_file_bytes"] == expected
