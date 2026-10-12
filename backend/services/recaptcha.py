"""Server-side Google reCAPTCHA v3 verification for PDF scans.

The frontend obtains a token via ``grecaptcha.execute(siteKey, {action: "scan_pdf"})``
and sends it with the upload; we verify it here before any (paid) processing runs.

If ``RECAPTCHA_SECRET_KEY`` is unset, verification is skipped (local dev / tests).
"""
import logging
import os

import httpx

logger = logging.getLogger(__name__)

VERIFY_URL = "https://www.google.com/recaptcha/api/siteverify"
SCAN_ACTION = "scan_pdf"

_SECRET = os.environ.get("RECAPTCHA_SECRET_KEY", "").strip()
_MIN_SCORE = float(os.environ.get("RECAPTCHA_MIN_SCORE", "0.5"))

if not _SECRET:
    logger.warning("RECAPTCHA_SECRET_KEY not set — reCAPTCHA verification is DISABLED")


async def verify_recaptcha(token: str | None, remote_ip: str | None = None, action: str = SCAN_ACTION) -> bool:
    """True if the token is valid, for the expected action, and scores above the threshold.

    Fails closed: a missing token, network error, or bad response all return False.
    """
    if not _SECRET:
        return True
    if not token:
        return False
    data = {"secret": _SECRET, "response": token}
    if remote_ip:
        data["remoteip"] = remote_ip
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(VERIFY_URL, data=data)
        result = resp.json()
    except Exception as e:  # noqa: BLE001
        logger.warning("reCAPTCHA verify request failed: %s", e)
        return False

    if not result.get("success"):
        logger.info("reCAPTCHA rejected: errors=%s", result.get("error-codes"))
        return False
    if result.get("action") != action:
        logger.info("reCAPTCHA action mismatch: got=%s expected=%s", result.get("action"), action)
        return False
    score = float(result.get("score", 0.0))
    if score < _MIN_SCORE:
        logger.info("reCAPTCHA score too low: %.2f < %.2f", score, _MIN_SCORE)
        return False
    return True
