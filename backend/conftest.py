"""
Set low rate limits before app is loaded so rate-limit tests can assert 429 quickly.
"""
import os

# Must be set before main is imported so decorators use these limits.
os.environ.setdefault("RATE_LIMIT_CHAT", "2/minute")
os.environ.setdefault("RATE_LIMIT_PROCESS_PDF", "2/minute")
os.environ.setdefault("RATE_LIMIT_EMAIL_SPREADSHEET", "100/minute")
os.environ.setdefault("RATE_LIMIT_EXPORT", "100/minute")
# Use in-memory rate limit storage in tests (no Redis).
os.environ.pop("REDIS_URL", None)

import pytest
from fastapi.testclient import TestClient

from auth import get_current_user, get_current_user_optional
from main import app


@pytest.fixture
def client():
    """Test client with auth overridden to a fixed test user."""
    def fake_get_current_user():
        return "test-user-id"

    app.dependency_overrides[get_current_user] = fake_get_current_user
    app.dependency_overrides[get_current_user_optional] = fake_get_current_user
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def affiliate_payment():
    """Keep webhook tests off the database: affiliate commission recording is mocked.

    Request this fixture by name to assert on the mock.
    """
    from unittest.mock import patch

    with patch("services.billing.record_affiliate_payment") as mock:
        yield mock


@pytest.fixture(autouse=True)
def no_live_analytics(monkeypatch):
    """backend/.env holds real GA4/LinkedIn secrets; tests must never send live conversions.

    Tests that exercise dispatch set their own fake secret with monkeypatch.setenv.
    """
    monkeypatch.delenv("GA4_API_SECRET", raising=False)
    monkeypatch.delenv("LINKEDIN_CAPI_TOKEN", raising=False)


@pytest.fixture(autouse=True)
def no_live_statement_meta():
    """Scans read the summary box with a real Gemini call; tests must never make it.

    Request this fixture by name to set a return value or assert on the mock.
    """
    from unittest.mock import patch

    with patch("main.extract_statement_meta", return_value=None) as mock:
        yield mock


@pytest.fixture(autouse=True)
def no_db_review_claim():
    """/api/usage looks up the review-reward claim; keep tests off the database.

    Request this fixture by name to set the status a test sees.
    """
    from unittest.mock import patch

    with patch("main.get_review_claim_status", return_value=None) as mock:
        yield mock
