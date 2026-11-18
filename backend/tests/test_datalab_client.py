"""Datalab client: upload via File Upload API, convert by reference, delete file + result."""
import httpx
import pytest

from services import datalab_client


class FakeDatalab:
    def __init__(self, convert_status="complete", put_status=200):
        self.calls = []
        self.convert_status = convert_status
        self.put_status = put_status

    def handler(self, request: httpx.Request) -> httpx.Response:
        m, p = request.method, request.url.path
        self.calls.append((m, p))
        if m == "POST" and p == "/api/v1/files/upload":
            return httpx.Response(200, json={"file_id": 42, "upload_url": "https://s3.test/put", "reference": "datalab://file-abc"})
        if m == "PUT" and request.url.host == "s3.test":
            return httpx.Response(self.put_status)
        if m == "GET" and p == "/api/v1/files/42/confirm":
            return httpx.Response(200, json={})
        if m == "POST" and p == "/api/v1/convert":
            self.convert_body = request.content.decode()
            return httpx.Response(200, json={"request_id": "req1"})
        if m == "GET" and p == "/api/v1/convert/req1":
            if self.convert_status == "complete":
                return httpx.Response(200, json={"status": "complete", "markdown": "# txns"})
            return httpx.Response(200, json={"status": "failed", "error": "bad pdf"})
        if m == "DELETE":
            return httpx.Response(204)
        return httpx.Response(404)


@pytest.fixture
def fake(monkeypatch):
    fd = FakeDatalab()
    real = httpx.Client
    monkeypatch.setattr(httpx, "Client", lambda *a, **k: real(transport=httpx.MockTransport(fd.handler)))
    monkeypatch.setenv("DATALAB_API_KEY", "k")
    monkeypatch.setattr(datalab_client, "POLL_INTERVAL_SEC", 0)
    return fd


def test_converts_by_reference_and_deletes_file_and_result(fake):
    assert datalab_client.convert_pdf_to_markdown(b"%PDF-1.4", "Acct 1234.pdf") == "# txns"
    assert "datalab%3A%2F%2Ffile-abc" in fake.convert_body or "datalab://file-abc" in fake.convert_body
    assert ("DELETE", "/api/v1/results/req1") in fake.calls
    assert ("DELETE", "/api/v1/files/42") in fake.calls


def test_failed_conversion_still_deletes_file(fake):
    fake.convert_status = "failed"
    with pytest.raises(RuntimeError):
        datalab_client.convert_pdf_to_markdown(b"%PDF-1.4")
    assert ("DELETE", "/api/v1/files/42") in fake.calls
    assert ("DELETE", "/api/v1/results/req1") in fake.calls


def test_failed_upload_deletes_partial_file(fake):
    fake.put_status = 500
    with pytest.raises(httpx.HTTPStatusError):
        datalab_client.convert_pdf_to_markdown(b"%PDF-1.4")
    assert ("DELETE", "/api/v1/files/42") in fake.calls
    assert not any(p == "/api/v1/convert" for _, p in fake.calls)
