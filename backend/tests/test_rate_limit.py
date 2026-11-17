"""Tests for rate limiting on /api/chat and /api/process-pdf."""
import uuid
from unittest.mock import patch

import pytest


TEST_JOB_ID = "00000000-0000-0000-0000-000000000001"
MINIMAL_PDF = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\nxref\n0 4\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n%%EOF"


@pytest.fixture
def mock_chat_deps():
    """Mock get_job and get_reply so /api/chat returns 200 without DB or LLM."""
    minimal_job = {
        "id": TEST_JOB_ID,
        "transactions": [],
        "csv_content": "date,description,amount,type,category\n",
        "raw_text": "",
        "currency": None,
    }

    with patch("main.get_job", return_value=minimal_job), patch(
        "main.get_reply", return_value=("Test reply", [])
    ):
        yield


def test_chat_rate_limit_returns_429_after_limit(client, mock_chat_deps):
    """After 2 requests per minute, the 3rd request to /api/chat returns 429."""
    url = "/api/chat"
    payload = {"job_id": TEST_JOB_ID, "message": "Hello"}

    r1 = client.post(url, json=payload)
    r2 = client.post(url, json=payload)
    r3 = client.post(url, json=payload)

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r3.status_code == 429
    assert "rate limit" in r3.json().get("error", "").lower() or "rate limit" in str(r3.json()).lower()


@pytest.fixture
def mock_process_pdf_deps():
    """Mock PDF extraction and store so /api/process-pdf returns 200 without real processing."""
    with patch("main.decrypt_pdf", side_effect=lambda c, p=None: c), patch(
        "main.extract_text_from_pdf", return_value="Date,Description,Debit,Credit\n1/1/24,Foo,10,0"
    ), patch(
        "main.extract_and_categorize", return_value=([], "USD")
    ), patch("main.create_job_id", return_value=str(uuid.uuid4())), patch("main.set_job"), patch(
        "main.sum_trial_pages_by_ip", return_value=0
    ), patch("main.record_trial_run"), patch("main.notify_scan"), patch(
        "main.ensure_free_grant", return_value={"plan_pages": 100}
    ), patch("main.deduct_pages", return_value={"plan_pages": 99}), patch("main.insert_usage_log"), patch("main.count_pdf_pages", return_value=1):
        yield


def test_process_pdf_rate_limit_returns_429_after_limit(client, mock_process_pdf_deps):
    """After 2 requests per minute, the 3rd request to /api/process-pdf returns 429."""
    url = "/api/process-pdf"
    files = {"file": ("statement.pdf", MINIMAL_PDF, "application/pdf")}
    data = {"scanned_method": "vision"}

    r1 = client.post(url, files=files, data=data)
    r2 = client.post(url, files=files, data=data)
    r3 = client.post(url, files=files, data=data)

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r3.status_code == 429
    assert "rate limit" in r3.json().get("error", "").lower() or "rate limit" in str(r3.json()).lower()


@pytest.mark.parametrize(
    "error",
    [
        __import__("httpx").ReadTimeout("timed out"),
        __import__("google.genai.errors", fromlist=["ServerError"]).ServerError(
            504, {"error": {"code": 504, "message": "The request timed out.", "status": "DEADLINE_EXCEEDED"}}
        ),
    ],
)
def test_chat_timeout_returns_504_with_retry_message(client, error):
    """A Gemini request that runs out of time gives a clear 504, not the generic 500."""
    import main

    main.limiter.reset()
    job = {"id": TEST_JOB_ID, "transactions": [{"description": "x"}]}
    with patch("main.get_job", return_value=job), patch("main.get_reply", side_effect=error):
        r = client.post("/api/chat", json={"job_id": TEST_JOB_ID, "message": "Hello"})
    assert r.status_code == 504
    assert r.json()["detail"] == main.CHAT_TIMEOUT_MESSAGE


def test_chat_client_has_request_timeout(monkeypatch):
    from services import chat_service as cs

    monkeypatch.setenv("GOOGLE_GEMINI_API_KEY", "test-key")
    assert cs._get_client()._api_client._http_options.timeout == cs.CHAT_REQUEST_TIMEOUT_MS == 60_000
