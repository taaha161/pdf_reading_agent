"""
Set low rate limits before app is loaded so rate-limit tests can assert 429 quickly.
"""
import os

# Must be set before main is imported so decorators use these limits.
os.environ.setdefault("RATE_LIMIT_CHAT", "2/minute")
os.environ.setdefault("RATE_LIMIT_PROCESS_PDF", "2/minute")

import pytest
from fastapi.testclient import TestClient

from auth import get_current_user
from main import app


@pytest.fixture
def client():
    """Test client with auth overridden to a fixed test user."""
    def fake_get_current_user():
        return "test-user-id"

    app.dependency_overrides[get_current_user] = fake_get_current_user
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()
