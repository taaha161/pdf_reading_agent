"""reCAPTCHA gate and page-based limits on /api/process-pdf.

Anonymous: FREE_ANON_PAGES per IP (not cookie). Signed in: free month, plan and pack pages.
Pages are counted before any processing.
"""
import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

import main
from main import FREE_ANON_PAGES, FREE_SIGNUP_PAGES, app, get_current_user_optional

MINIMAL_PDF = b"%PDF-1.4\n%%EOF"


@pytest.fixture
def anon_client():
    """Unauthenticated client; per-IP free pages live in an in-memory Counter.
    Set `client.pages` to control the page count of the next upload."""
    used = Counter()

    def record(job_id, ip_hash=None, pages=None):
        used[ip_hash] += pages or 0

    main.limiter.reset()
    with patch("main.decrypt_pdf", side_effect=lambda c, p=None: c), patch(
        "main.extract_text_from_pdf", return_value="1/1/24,Foo,10"
    ) as extract, patch(
        "main.extract_and_categorize", return_value=([], "USD")
    ), patch("main.create_job_id", side_effect=lambda: str(uuid.uuid4())), patch(
        "main.notify_scan"
    ), patch("main.sum_trial_pages_by_ip", side_effect=lambda h: used[h]), patch(
        "main.record_trial_run", side_effect=record
    ), patch("main.limiter.enabled", False):
        with TestClient(app) as c:
            c.pages = 1
            c.extract = extract
            with patch("main.count_pdf_pages", side_effect=lambda _content: c.pages):
                yield c
    app.dependency_overrides.pop(get_current_user_optional, None)


def _scan(client, ip, **extra):
    return client.post(
        "/api/process-pdf",
        files={"file": ("s.pdf", MINIMAL_PDF, "application/pdf")},
        data={"recaptcha_token": "tok", **extra},
        headers={"cf-connecting-ip": ip},
    )


def _billing(free=0, plan=0, pack=0, expires_in_days=30):
    return {
        "user_id": "user-1",
        "free_pages": free,
        "free_expires_at": datetime.now(timezone.utc) + timedelta(days=expires_in_days),
        "plan_pages": plan,
        "pack_pages": pack,
        "stripe_subscription_id": None,
    }


def test_anonymous_free_pages_are_per_ip_and_ignore_cookies(anon_client):
    anon_client.pages = FREE_ANON_PAGES
    r = _scan(anon_client, "1.1.1.1")
    assert r.status_code == 200
    assert r.json()["trial_remaining"] == 0
    assert r.json()["pages_charged"] == FREE_ANON_PAGES

    # Clearing / forging cookies doesn't reset the count.
    anon_client.cookies.clear()
    anon_client.cookies.set("trial_pdf_used", "0")
    anon_client.pages = 1
    r = _scan(anon_client, "1.1.1.1")
    assert r.status_code == 401
    assert r.json()["detail"]["code"] == "TRIAL_LIMIT"
    assert "trial limit" in r.json()["detail"]["detail"].lower()

    # A different IP has its own allowance.
    assert _scan(anon_client, "2.2.2.2").status_code == 200


def test_anonymous_pdf_bigger_than_free_pages_is_rejected_before_processing(anon_client):
    anon_client.pages = FREE_ANON_PAGES + 1
    r = _scan(anon_client, "6.6.6.6")
    assert r.status_code == 401
    detail = r.json()["detail"]
    assert detail["code"] == "FREE_PAGES_EXCEEDED"
    assert (detail["pages_required"], detail["pages_remaining"]) == (FREE_ANON_PAGES + 1, FREE_ANON_PAGES)
    anon_client.extract.assert_not_called()


def test_accurate_mode_costs_two_pages_per_page(anon_client):
    anon_client.pages = 4
    r = _scan(anon_client, "7.7.7.7", conversion_mode="accurate")
    assert r.status_code == 200
    assert r.json()["pages_charged"] == 8
    assert r.json()["trial_remaining"] == FREE_ANON_PAGES - 8


def test_signed_in_scan_deducts_pages(anon_client):
    app.dependency_overrides[get_current_user_optional] = lambda: "user-1"
    anon_client.pages = 12
    after = _billing(free=FREE_SIGNUP_PAGES - 12)
    with patch("main.ensure_free_grant", return_value=_billing(free=FREE_SIGNUP_PAGES)), patch(
        "main.deduct_pages", return_value=after
    ) as deduct, patch("main.set_job"), patch("main.insert_usage_log"):
        r = _scan(anon_client, "5.5.5.5")
    assert r.status_code == 200
    deduct.assert_called_once_with("user-1", 12)
    body = r.json()
    assert body["pages_charged"] == 12
    assert body["pages_remaining"] == FREE_SIGNUP_PAGES - 12


def test_signed_in_not_enough_pages_is_rejected_before_processing(anon_client):
    app.dependency_overrides[get_current_user_optional] = lambda: "user-1"
    anon_client.pages = 20
    with patch("main.ensure_free_grant", return_value=_billing(plan=5, pack=10)), patch("main.deduct_pages") as deduct:
        r = _scan(anon_client, "5.5.5.5")
    assert r.status_code == 402
    detail = r.json()["detail"]
    assert detail["code"] == "INSUFFICIENT_CREDITS"
    assert (detail["pages_required"], detail["pages_remaining"]) == (20, 15)
    deduct.assert_not_called()
    anon_client.extract.assert_not_called()


def test_expired_free_pages_do_not_count(anon_client):
    app.dependency_overrides[get_current_user_optional] = lambda: "user-1"
    with patch("main.ensure_free_grant", return_value=_billing(free=100, expires_in_days=-1)):
        r = _scan(anon_client, "5.5.5.5")
    assert r.status_code == 402


def test_trial_fails_closed_when_count_unavailable(anon_client):
    with patch("main.sum_trial_pages_by_ip", side_effect=RuntimeError("db down")):
        assert _scan(anon_client, "3.3.3.3").status_code == 401


def test_scan_rejected_when_recaptcha_fails(anon_client):
    with patch("main.verify_recaptcha", new=AsyncMock(return_value=False)) as verify:
        r = _scan(anon_client, "4.4.4.4")
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "RECAPTCHA_FAILED"
    verify.assert_awaited_once_with("tok", "4.4.4.4")
