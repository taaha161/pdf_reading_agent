"""Background scans: POST /api/scans starts one, GET /api/scans/{id} reports progress/result."""
import io
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter

import main
from main import app, get_current_user_optional
from services import scan_jobs


def _pdf(user_password: str | None = None) -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    if user_password:
        writer.encrypt(user_password=user_password, owner_password="owner-secret")
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


TX = [{"date": "2024-01-01", "description": "Coffee", "amount": "4.50", "type": "debit", "category": "Other"}]


def _fake_extract(raw_text, on_chunk=None):
    for i in (1, 2):
        on_chunk(i, 2)
    return TX, "USD"


@pytest.fixture
def client():
    scan_jobs.clear_all()
    stages = []
    real_set_stage = scan_jobs.set_stage

    def record_stage(scan_id, stage, chunk=None, chunks=None):
        stages.append((stage, chunk, chunks))
        real_set_stage(scan_id, stage, chunk, chunks)

    with patch("main.verify_recaptcha", AsyncMock(return_value=True)), patch(
        "main.extract_text_from_pdf", return_value="1/1/24,Coffee,4.50"
    ), patch("main.extract_and_categorize", side_effect=_fake_extract), patch("main.notify_scan"), patch(
        "main.count_trial_runs_by_ip", return_value=0
    ), patch("main.record_trial_run"), patch("main.set_scan_stage", side_effect=record_stage), patch(
        "main.limiter.enabled", False
    ):
        with TestClient(app) as c:
            c.stages = stages
            yield c
    app.dependency_overrides.pop(get_current_user_optional, None)


def _start(client, pdf=None, **data):
    return client.post(
        "/api/scans",
        files={"file": ("s.pdf", pdf or _pdf(), "application/pdf")},
        data={"recaptcha_token": "tok", **data},
        headers={"cf-connecting-ip": "9.9.9.9"},
    )


def test_scan_runs_in_background_and_reports_result(client):
    r = _start(client)
    assert r.status_code == 202
    scan_id = r.json()["scan_id"]

    # TestClient runs background tasks before returning, so the scan is finished.
    status = client.get(f"/api/scans/{scan_id}").json()
    assert status["status"] == "done"
    assert status["result"]["transactions"][0]["description"] == "Coffee"
    assert status["result"]["currency"] == "USD"
    assert client.stages == [
        ("reading", None, None),
        ("extracting", None, None),
        ("extracting", 1, 2),
        ("extracting", 2, 2),
        ("finalizing", None, None),
    ]


def test_password_errors_return_before_scan_starts(client):
    locked = _pdf("open-me")
    r = _start(client, locked)
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "PDF_PASSWORD_REQUIRED"

    r = _start(client, locked, pdf_password="nope")
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "PDF_PASSWORD_INCORRECT"
    assert client.stages == []

    r = _start(client, locked, pdf_password="open-me")
    assert r.status_code == 202
    assert client.get(f"/api/scans/{r.json()['scan_id']}").json()["status"] == "done"


def test_pipeline_failure_is_reported_as_scan_error(client):
    with patch("main.extract_and_categorize", side_effect=RuntimeError("gemini down")):
        scan_id = _start(client).json()["scan_id"]
    status = client.get(f"/api/scans/{scan_id}").json()
    assert status["status"] == "error"
    assert status["error"] == {"status_code": 500, "detail": main.GENERIC_500_MESSAGE}


def test_scan_is_private_to_its_owner(client):
    scan_id = _start(client).json()["scan_id"]  # anonymous scan
    app.dependency_overrides[get_current_user_optional] = lambda: "someone-else"
    assert client.get(f"/api/scans/{scan_id}").status_code == 404
    assert client.get("/api/scans/does-not-exist").status_code == 404
