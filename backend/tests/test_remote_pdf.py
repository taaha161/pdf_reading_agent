"""Fetching a statement PDF from a URL: share-link normalization, SSRF guard, size/type checks."""
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

import main
from main import app
from services import remote_pdf
from services.remote_pdf import RemotePdfError, fetch_pdf, normalize_share_url

PDF = b"%PDF-1.4\n%%EOF"


def test_normalize_google_drive_share_link():
    url = normalize_share_url("https://drive.google.com/file/d/AbC_123-x/view?usp=sharing")
    assert url == "https://drive.usercontent.google.com/download?id=AbC_123-x&export=download&confirm=t"
    url = normalize_share_url("https://drive.google.com/open?id=XYZ")
    assert "id=XYZ" in url


def test_normalize_dropbox_link():
    url = normalize_share_url("https://www.dropbox.com/s/abc/stmt.pdf?dl=0")
    assert url.endswith("dl=1")


def test_other_urls_unchanged():
    assert normalize_share_url("https://example.com/a.pdf") == "https://example.com/a.pdf"


def _public_dns():
    return patch.object(remote_pdf, "_resolve_public_ip", AsyncMock(return_value="93.184.216.34"))


def _run(url, handler, max_bytes=1000):
    import asyncio

    return asyncio.run(fetch_pdf(url, max_bytes, transport=httpx.MockTransport(handler)))


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/a.pdf",
        "http://169.254.169.254/latest/meta-data",
        "http://10.0.0.5/a.pdf",
        "http://[::1]/a.pdf",
        "http://[::ffff:127.0.0.1]/a.pdf",
    ],
)
def test_private_ip_literals_rejected(url):
    with pytest.raises(RemotePdfError, match="private"):
        _run(url, lambda r: httpx.Response(200, content=PDF))


def test_hostname_resolving_to_private_rejected():
    async def fake_getaddrinfo(host, port, type=0):
        return [(2, 1, 6, "", ("192.168.1.1", port))]

    with patch("asyncio.BaseEventLoop.getaddrinfo", side_effect=fake_getaddrinfo):
        with pytest.raises(RemotePdfError, match="private"):
            _run("https://internal.example/a.pdf", lambda r: httpx.Response(200, content=PDF))


@pytest.mark.parametrize("url", ["ftp://example.com/a.pdf", "file:///etc/passwd", "https://example.com:8443/a.pdf", "https://u:p@example.com/a.pdf"])
def test_bad_schemes_ports_credentials_rejected(url):
    with pytest.raises(RemotePdfError):
        _run(url, lambda r: httpx.Response(200, content=PDF))


def test_success_pins_ip_and_keeps_host_and_filename():
    seen = {}

    def handler(request):
        seen["host"] = request.url.host
        seen["header"] = request.headers["host"]
        return httpx.Response(200, content=PDF, headers={"content-disposition": 'attachment; filename="My Stmt.pdf"'})

    with _public_dns():
        content, name = _run("https://example.com/x", handler)
    assert content == PDF
    assert name == "My Stmt.pdf"
    assert seen == {"host": "93.184.216.34", "header": "example.com"}


def test_redirect_to_private_rejected():
    def handler(request):
        return httpx.Response(302, headers={"location": "http://127.0.0.1/secret"})

    real = remote_pdf._resolve_public_ip

    async def resolve(host, port):
        return "93.184.216.34" if host == "example.com" else await real(host, port)

    with patch.object(remote_pdf, "_resolve_public_ip", side_effect=resolve):
        with pytest.raises(RemotePdfError, match="private"):
            _run("https://example.com/a.pdf", handler)


def test_non_pdf_rejected():
    with _public_dns(), pytest.raises(RemotePdfError, match="didn't return a PDF"):
        _run("https://example.com/a.pdf", lambda r: httpx.Response(200, content=b"<html>login</html>"))


def test_too_large_rejected():
    with _public_dns(), pytest.raises(RemotePdfError, match="too large"):
        _run("https://example.com/a.pdf", lambda r: httpx.Response(200, content=PDF + b"0" * 2000))


def test_endpoint_returns_pdf_bytes():
    main.limiter.reset()
    with patch("main.fetch_pdf", AsyncMock(return_value=(PDF, "s.pdf"))):
        with TestClient(app) as c:
            r = c.post("/api/fetch-pdf-url", json={"url": "https://example.com/s.pdf"})
    assert r.status_code == 200
    assert r.content == PDF
    assert r.headers["x-filename"] == "s.pdf"


def test_endpoint_maps_errors_to_400():
    main.limiter.reset()
    with patch("main.fetch_pdf", AsyncMock(side_effect=RemotePdfError("nope"))):
        with TestClient(app) as c:
            r = c.post("/api/fetch-pdf-url", json={"url": "https://example.com/s.pdf"})
    assert r.status_code == 400
    assert r.json()["detail"] == "nope"
