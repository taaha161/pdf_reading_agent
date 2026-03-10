"""Datalab API client: PDF to markdown via Convert API."""
import logging
import os
import time

logger = logging.getLogger("datalab_client")

DEFAULT_BASE_URL = "https://www.datalab.to"
POLL_INTERVAL_SEC = 2
POLL_MAX_WAIT_SEC = 300  # 5 minutes


# Datalab processing modes: fast (default), balanced, accurate (see https://documentation.datalab.to/docs/welcome/sdk/conversion)
VALID_MODES = ("fast", "balanced", "accurate")


def convert_pdf_to_markdown(
    file_content: bytes,
    filename: str = "statement.pdf",
    mode: str = "fast",
) -> str:
    """
    Convert PDF to markdown using Datalab Convert API.
    Requires DATALAB_API_KEY. Optional: DATALAB_BASE_URL.
    mode: "fast" | "balanced" | "accurate" (processing mode; default "fast").
    Returns markdown string. Raises on API error or timeout.
    """
    t0 = time.perf_counter()
    api_key = os.environ.get("DATALAB_API_KEY", "").strip()
    if not api_key:
        raise ValueError("DATALAB_API_KEY is not set")
    base_url = os.environ.get("DATALAB_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    mode_val = (mode or "fast").strip().lower()
    if mode_val not in VALID_MODES:
        mode_val = "fast"

    import httpx

    headers = {"X-API-Key": api_key}
    convert_url = f"{base_url}/api/v1/convert"

    logger.info("convert_pdf_to_markdown: submitting file=%s, size=%d, mode=%s (elapsed %.2f s)", filename, len(file_content), mode_val, time.perf_counter() - t0)
    with httpx.Client(timeout=60.0) as client:
        resp = client.post(
            convert_url,
            files={"file": (filename or "statement.pdf", file_content, "application/pdf")},
            data={"output_format": "markdown", "mode": mode_val},
            headers=headers,
        )
        resp.raise_for_status()
        data = resp.json()
    request_id = data.get("request_id")
    if not request_id:
        raise RuntimeError("Datalab convert response missing request_id")
    check_url = f"{base_url}/api/v1/convert/{request_id}"
    logger.info("convert_pdf_to_markdown: polling request_id=%s (elapsed %.2f s)", request_id, time.perf_counter() - t0)

    started = time.monotonic()
    while True:
        if time.monotonic() - started > POLL_MAX_WAIT_SEC:
            raise TimeoutError(f"Datalab convert did not complete within {POLL_MAX_WAIT_SEC}s")
        time.sleep(POLL_INTERVAL_SEC)
        with httpx.Client(timeout=30.0) as client:
            poll_resp = client.get(check_url, headers=headers)
            poll_resp.raise_for_status()
            result = poll_resp.json()
        status = (result.get("status") or "").lower()
        if status == "complete":
            markdown = result.get("markdown") or ""
            logger.info("convert_pdf_to_markdown: done, markdown len=%d (%.2f s total)", len(markdown), time.perf_counter() - t0)
            return markdown
        if status == "failed":
            err = result.get("error", "Unknown error")
            raise RuntimeError(f"Datalab convert failed: {err}")
        logger.debug("convert_pdf_to_markdown: status=%s, waiting...", status)
