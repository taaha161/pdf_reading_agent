"""Monitoring: off without a DSN, and nothing sensitive leaves in events."""
from unittest.mock import patch

from fastapi import HTTPException

import main
from services import monitoring


def test_disabled_without_dsn(monkeypatch):
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    assert monitoring.init_monitoring() is False


def test_redact_filenames():
    msg = "scan: request started, filename=Moniepoint MFB 8151183521 (Apr 2024 - Apr 2026).pdf, scanned_method=vision"
    out = monitoring.redact(msg)
    assert "8151183521" not in out
    assert "filename=[redacted], scanned_method=vision" in out
    assert monitoring.redact("submitting file=Sept 2025.pdf, size=1") == "submitting file=[redacted], size=1"
    assert monitoring.redact(None) is None


def test_before_send_strips_body_cookies_headers_and_locals():
    event = {
        "request": {
            "data": {"file": "PDF BYTES"},
            "cookies": {"sb": "x"},
            "headers": {"Authorization": "Bearer abc", "User-Agent": "ua", "cf-connecting-ip": "1.2.3.4"},
        },
        "logentry": {"message": "start filename=%s", "params": ["a.pdf"], "formatted": "start filename=Acct 123.pdf, x=1"},
        "exception": {"values": [{"value": "bad filename=Acct 123.pdf, x", "stacktrace": {"frames": [{"vars": {"raw_text": "TXNS"}}]}}]},
        "breadcrumbs": {"values": [{"message": "submitting file=Acct 123.pdf, size=1"}]},
    }
    out = monitoring.before_send(event, {})
    req = out["request"]
    assert "data" not in req and "cookies" not in req
    assert req["headers"]["Authorization"] == "[redacted]"
    assert req["headers"]["cf-connecting-ip"] == "[redacted]"
    assert req["headers"]["User-Agent"] == "ua"
    assert "123" not in out["logentry"]["formatted"]
    exc = out["exception"]["values"][0]
    assert "123" not in exc["value"]
    assert "vars" not in exc["stacktrace"]["frames"][0]
    assert "123" not in out["breadcrumbs"]["values"][0]["message"]


def test_scan_failure_reported_for_timeout():
    err = HTTPException(422, detail={"detail": "This PDF took too long to read.", "code": "PDF_EXTRACTION_TIMEOUT"})
    with patch("main.capture_monitoring_message") as cap:
        main._report_scan_failure("scan1", "user1", err)
    cap.assert_called_once()
    assert cap.call_args.kwargs["error_code"] == "PDF_EXTRACTION_TIMEOUT"
    assert cap.call_args.kwargs["user_id"] == "user1"


def test_scan_failure_not_reported_for_password_or_non_422():
    with patch("main.capture_monitoring_message") as cap:
        main._report_scan_failure("s", None, HTTPException(422, detail={"detail": "pw", "code": "PDF_PASSWORD_REQUIRED"}))
        main._report_scan_failure("s", None, HTTPException(402, detail="credits"))
        main._report_scan_failure("s", None, HTTPException(500, detail="boom"))
    cap.assert_not_called()
