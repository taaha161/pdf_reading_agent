"""Download a PDF from a user-supplied URL, safely.

Used by POST /api/fetch-pdf-url so users can scan a statement from a link
(Google Drive / Dropbox share links, or any direct PDF URL) instead of a local file.

SSRF protection: only http(s) on default ports, every hop's hostname is resolved and
all addresses must be public; the connection is pinned to the vetted IP (TLS still
verifies the real hostname via SNI), so DNS rebinding between check and connect
cannot redirect us to an internal address. Redirects are followed manually and each
hop is re-validated. The body is streamed with a hard size cap.
"""
from __future__ import annotations

import asyncio
import ipaddress
import re
import socket
from urllib.parse import parse_qs, unquote, urlencode, urlsplit, urlunsplit

import httpx

MAX_REDIRECTS = 5
TIMEOUT = httpx.Timeout(20.0, connect=5.0)
USER_AGENT = "BankStatementScanner/1.0 (+https://bankstatementscanner.com)"


class RemotePdfError(Exception):
    """User-facing error (message is safe to show)."""


class RemotePdfTooLarge(RemotePdfError):
    """The remote PDF exceeds max_bytes. size_bytes is the declared or downloaded-so-far size."""

    def __init__(self, size_bytes: int, max_bytes: int):
        super().__init__(f"That PDF is too large (max {max_bytes // (1024 * 1024)} MB).")
        self.size_bytes = size_bytes
        self.max_bytes = max_bytes


_GDRIVE_FILE_RE = re.compile(r"^/file/d/([A-Za-z0-9_-]+)")


def normalize_share_url(url: str) -> str:
    """Turn common share-page links into direct-download links."""
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    query = parse_qs(parts.query)

    if host in ("drive.google.com", "docs.google.com"):
        file_id = None
        m = _GDRIVE_FILE_RE.match(parts.path)
        if m:
            file_id = m.group(1)
        elif query.get("id"):
            file_id = query["id"][0]
        if file_id:
            return "https://drive.usercontent.google.com/download?" + urlencode(
                {"id": file_id, "export": "download", "confirm": "t"}
            )

    if host in ("dropbox.com", "www.dropbox.com"):
        query.pop("dl", None)
        query["dl"] = ["1"]
        return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query, doseq=True), ""))

    return url


def _is_public_ip(ip: ipaddress._BaseAddress) -> bool:
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    return ip.is_global and not ip.is_multicast


async def _resolve_public_ip(host: str, port: int) -> str:
    """Resolve host; reject if ANY address is non-public. Returns one vetted IP."""
    try:
        literal = ipaddress.ip_address(host)
        if not _is_public_ip(literal):
            raise RemotePdfError("That URL points to a private address and can't be fetched.")
        return str(literal)
    except ValueError:
        pass
    loop = asyncio.get_running_loop()
    try:
        infos = await loop.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror:
        raise RemotePdfError("Couldn't find that website. Check the URL and try again.")
    ips = {info[4][0] for info in infos}
    if not ips:
        raise RemotePdfError("Couldn't find that website. Check the URL and try again.")
    for ip in ips:
        if not _is_public_ip(ipaddress.ip_address(ip)):
            raise RemotePdfError("That URL points to a private address and can't be fetched.")
    return sorted(ips)[0]


def _validate_url(url: str) -> tuple[str, str, int]:
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https"):
        raise RemotePdfError("Only http:// and https:// links are supported.")
    if not parts.hostname:
        raise RemotePdfError("That doesn't look like a valid URL.")
    if parts.username or parts.password:
        raise RemotePdfError("URLs with embedded credentials aren't supported.")
    default_port = 443 if parts.scheme == "https" else 80
    port = parts.port or default_port
    if port != default_port:
        raise RemotePdfError("Only standard web ports are supported.")
    return parts.scheme, parts.hostname, port


def _filename_from(response: httpx.Response, url: str) -> str:
    cd = response.headers.get("content-disposition", "")
    m = re.search(r"filename\*=UTF-8''([^;]+)", cd, re.I) or re.search(r'filename="?([^";]+)"?', cd, re.I)
    name = unquote(m.group(1)) if m else unquote(urlsplit(url).path.rsplit("/", 1)[-1])
    name = re.sub(r"[^\w.\- ()]+", "_", name, flags=re.ASCII).strip(" ._")[:120]
    if not name:
        name = "statement"
    if not name.lower().endswith(".pdf"):
        name += ".pdf"
    return name


async def fetch_pdf(url: str, max_bytes: int, transport: httpx.AsyncBaseTransport | None = None) -> tuple[bytes, str]:
    """Download a PDF. Returns (content, filename). Raises RemotePdfError on any failure."""
    url = (url or "").strip()
    if len(url) > 2048:
        raise RemotePdfError("That URL is too long.")
    url = normalize_share_url(url)

    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=False, transport=transport) as client:
        for _ in range(MAX_REDIRECTS + 1):
            scheme, host, port = _validate_url(url)
            ip = await _resolve_public_ip(host, port)
            ip_host = f"[{ip}]" if ":" in ip else ip
            parts = urlsplit(url)
            pinned = urlunsplit((scheme, ip_host, parts.path or "/", parts.query, ""))
            headers = {"Host": parts.netloc, "User-Agent": USER_AGENT, "Accept": "application/pdf,*/*"}
            extensions = {"sni_hostname": host} if scheme == "https" else {}
            try:
                async with client.stream("GET", pinned, headers=headers, extensions=extensions) as resp:
                    if resp.is_redirect:
                        location = resp.headers.get("location")
                        if not location:
                            raise RemotePdfError("The link redirected somewhere invalid.")
                        url = str(httpx.URL(url).join(location))
                        continue
                    if resp.status_code in (401, 403):
                        raise RemotePdfError(
                            "Access denied. Make sure the file is shared publicly "
                            "(e.g. \"Anyone with the link\"), or use the Google Drive button."
                        )
                    if resp.status_code == 404:
                        raise RemotePdfError("File not found at that URL.")
                    if resp.status_code >= 400:
                        raise RemotePdfError(f"The website returned an error ({resp.status_code}).")

                    declared = resp.headers.get("content-length")
                    if declared and declared.isdigit() and int(declared) > max_bytes:
                        raise RemotePdfTooLarge(int(declared), max_bytes)
                    buf = bytearray()
                    async for chunk in resp.aiter_bytes():
                        buf.extend(chunk)
                        if len(buf) > max_bytes:
                            raise RemotePdfTooLarge(len(buf), max_bytes)
                    content = bytes(buf)
                    if b"%PDF-" not in content[:1024]:
                        raise RemotePdfError(
                            "That link didn't return a PDF. If it's a share link, make sure it's "
                            "public (\"Anyone with the link\"), or use the Google Drive button."
                        )
                    return content, _filename_from(resp, url)
            except httpx.TimeoutException:
                raise RemotePdfError("The website took too long to respond.")
            except httpx.HTTPError:
                raise RemotePdfError("Couldn't download from that URL.")
        raise RemotePdfError("Too many redirects.")
