"""reCAPTCHA gate and per-IP (not cookie) free-scan limit on /api/process-pdf."""
import uuid
from collections import Counter
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

import main
from main import TRIAL_LIMIT, app

MINIMAL_PDF = b"%PDF-1.4\n%%EOF"


@pytest.fixture
def anon_client():
    """Unauthenticated client; per-IP trial counts live in an in-memory Counter."""
    runs = Counter()

    def record(job_id, ip_hash=None):
        runs[ip_hash] += 1

    main.limiter.reset()
    with patch("main.extract_text_from_pdf", return_value="1/1/24,Foo,10"), patch(
        "main.extract_and_categorize", return_value=([], "USD")
    ), patch("main.create_job_id", side_effect=lambda: str(uuid.uuid4())), patch(
        "main.notify_scan"
    ), patch("main.count_trial_runs_by_ip", side_effect=lambda h: runs[h]), patch(
        "main.record_trial_run", side_effect=record
    ), patch("main.limiter.enabled", False):
        with TestClient(app) as c:
            yield c


def _scan(client, ip, **extra):
    return client.post(
        "/api/process-pdf",
        files={"file": ("s.pdf", MINIMAL_PDF, "application/pdf")},
        data={"recaptcha_token": "tok", **extra},
        headers={"cf-connecting-ip": ip},
    )


def test_trial_limit_is_per_ip_and_ignores_cookies(anon_client):
    for _ in range(TRIAL_LIMIT):
        assert _scan(anon_client, "1.1.1.1").status_code == 200

    # Clearing / forging cookies doesn't reset the count.
    anon_client.cookies.clear()
    anon_client.cookies.set("trial_pdf_used", "0")
    r = _scan(anon_client, "1.1.1.1")
    assert r.status_code == 401
    assert "trial limit" in r.json()["detail"].lower()

    # A different IP has its own allowance.
    assert _scan(anon_client, "2.2.2.2").status_code == 200


def test_trial_fails_closed_when_count_unavailable(anon_client):
    with patch("main.count_trial_runs_by_ip", side_effect=RuntimeError("db down")):
        assert _scan(anon_client, "3.3.3.3").status_code == 401


def test_scan_rejected_when_recaptcha_fails(anon_client):
    with patch("main.verify_recaptcha", new=AsyncMock(return_value=False)) as verify:
        r = _scan(anon_client, "4.4.4.4")
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "RECAPTCHA_FAILED"
    verify.assert_awaited_once_with("tok", "4.4.4.4")
