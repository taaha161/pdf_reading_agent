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

    # Upload via the File Upload API instead of attaching the PDF to the convert
    # request: files attached directly stay on Datalab for ~1 day and can't be
    # deleted, while uploaded files can be deleted as soon as we're done.
    logger.info("convert_pdf_to_markdown: uploading size=%d, mode=%s", len(file_content), mode_val)
    file_id, reference = _upload_file(base_url, file_content, headers)
    try:
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(
                f"{base_url}/api/v1/convert",
                data={"file_url": reference, "output_format": "markdown", "mode": mode_val},
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
        request_id = data.get("request_id")
        if not request_id:
            raise RuntimeError("Datalab convert response missing request_id")
        check_url = f"{base_url}/api/v1/convert/{request_id}"
        logger.info("convert_pdf_to_markdown: polling request_id=%s (elapsed %.2f s)", request_id, time.perf_counter() - t0)
        try:
            return _poll_result(check_url, headers, t0)
        finally:
            _delete_result(base_url, request_id, headers)
    finally:
        _delete_file(base_url, file_id, headers)


def _upload_file(base_url: str, file_content: bytes, headers: dict) -> tuple[str, str]:
    """Upload the PDF to Datalab storage. Returns (file_id, datalab:// reference)."""
    import httpx

    with httpx.Client(timeout=60.0) as client:
        # Generic name: real filenames often contain account numbers.
        resp = client.post(
            f"{base_url}/api/v1/files/upload",
            json={"filename": "statement.pdf", "content_type": "application/pdf"},
            headers=headers,
        )
        resp.raise_for_status()
        meta = resp.json()
        file_id, upload_url, reference = meta.get("file_id"), meta.get("upload_url"), meta.get("reference")
        if file_id is None or not upload_url or not reference:
            raise RuntimeError("Datalab file upload response missing file_id/upload_url/reference")
        file_id = str(file_id)
        try:
            put = client.put(upload_url, content=file_content, headers={"Content-Type": "application/pdf"})
            put.raise_for_status()
            confirm = client.get(f"{base_url}/api/v1/files/{file_id}/confirm", headers=headers)
            confirm.raise_for_status()
        except Exception:
            _delete_file(base_url, file_id, headers)
            raise
    return file_id, reference


def _poll_result(check_url: str, headers: dict, t0: float) -> str:
    import httpx

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


def _delete_file(base_url: str, file_id: str, headers: dict) -> None:
    """Delete the uploaded PDF from Datalab. Best-effort, like _delete_result."""
    import httpx

    try:
        with httpx.Client(timeout=10.0) as client:
            r = client.delete(f"{base_url}/api/v1/files/{file_id}", headers=headers)
        if r.status_code >= 400 and r.status_code != 404:
            logger.error("datalab: delete file %s failed (%s)", file_id, r.status_code)  # statement left on Datalab ~1 day
    except Exception as e:  # noqa: BLE001
        logger.error("datalab: delete file %s error: %s", file_id, e)


def _delete_result(base_url: str, request_id: str, headers: dict) -> None:
    """Delete the result from Datalab right away instead of letting it sit there
    for ~1 day (their default). Best-effort: a failure here never fails a scan."""
    import httpx

    try:
        with httpx.Client(timeout=10.0) as client:
            r = client.delete(f"{base_url}/api/v1/results/{request_id}", headers=headers)
        if r.status_code >= 400 and r.status_code != 404:
            logger.warning("datalab: delete result %s failed (%s)", request_id, r.status_code)
    except Exception as e:  # noqa: BLE001
        logger.warning("datalab: delete result %s error: %s", request_id, e)
