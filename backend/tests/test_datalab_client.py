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


def test_delete_file_retries_then_succeeds(fake, monkeypatch):
    monkeypatch.setattr(datalab_client, "DELETE_RETRY_DELAY_SEC", 0)
    responses = iter([500, 502, 204])
    orig = fake.handler

    def flaky(request):
        if request.method == "DELETE" and request.url.path == "/api/v1/files/42":
            fake.calls.append(("DELETE", request.url.path))
            return httpx.Response(next(responses))
        return orig(request)

    fake.handler = flaky
    assert datalab_client._delete_file("https://www.datalab.to", "42", {}) is True
    assert fake.calls.count(("DELETE", "/api/v1/files/42")) == 3


def test_delete_file_gives_up_without_raising(fake, monkeypatch):
    monkeypatch.setattr(datalab_client, "DELETE_RETRY_DELAY_SEC", 0)
    orig = fake.handler
    fake.handler = lambda r: httpx.Response(500) if r.method == "DELETE" else orig(r)
    assert datalab_client._delete_file("https://www.datalab.to", "42", {}) is False


def test_sweep_deletes_only_stale_files_across_pages(fake):
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    old = (now - timedelta(hours=2)).isoformat()
    fresh = (now - timedelta(minutes=1)).isoformat()
    pages = {
        0: [{"file_id": 1, "created": old}, {"file_id": 2, "created": fresh}],
        2: [{"file_id": 3, "created": old.replace("+00:00", "")}],  # naive timestamp
    }
    orig = fake.handler

    def handler(request):
        if request.method == "GET" and request.url.path == "/api/v1/files":
            off = int(request.url.params.get("offset", 0))
            fake.calls.append(("LIST", off))
            return httpx.Response(200, json={"files": pages.get(off, []), "total": 3, "limit": 100, "offset": off})
        return orig(request)

    fake.handler = handler
    assert datalab_client.sweep_stale_files() == 2
    assert ("DELETE", "/api/v1/files/1") in fake.calls
    assert ("DELETE", "/api/v1/files/3") in fake.calls
    assert ("DELETE", "/api/v1/files/2") not in fake.calls


def test_sweep_without_api_key_is_noop(monkeypatch):
    monkeypatch.delenv("DATALAB_API_KEY", raising=False)
    assert datalab_client.sweep_stale_files() == 0
