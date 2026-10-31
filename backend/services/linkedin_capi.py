"""LinkedIn Conversions API: server-side subscription purchase conversions.

Best-effort like notifications: every send runs on a daemon thread and swallows
all errors, so a LinkedIn outage never blocks or fails a Stripe webhook.

Env:
  LINKEDIN_CAPI_TOKEN               -- OAuth access token with rw_conversions scope
                                       (if unset, conversions are silently disabled).
  LINKEDIN_PURCHASE_CONVERSION_ID   -- Campaign Manager conversion rule ID (Conversions API type).
  LINKEDIN_API_VERSION              -- LinkedIn-Version header, YYYYMM (default: 202609).
"""

import hashlib
import logging
import os
import threading
import time

import httpx

logger = logging.getLogger("pdf_processor_app.linkedin_capi")

_ENDPOINT = "https://api.linkedin.com/rest/conversionEvents"


def _token() -> str:
    return os.environ.get("LINKEDIN_CAPI_TOKEN", "").strip()


def _purchase_conversion_id() -> str:
    return os.environ.get("LINKEDIN_PURCHASE_CONVERSION_ID", "").strip()


def _api_version() -> str:
    return os.environ.get("LINKEDIN_API_VERSION", "202609").strip()


def build_event(
    conversion_id: str,
    email: str,
    event_id: str | None,
    happened_at_ms: int,
    amount_cents: int | None = None,
    currency: str = "usd",
) -> dict:
    """Conversion event payload. Email is normalized and SHA-256 hashed as LinkedIn requires."""
    hashed = hashlib.sha256(email.strip().lower().encode()).hexdigest()
    event = {
        "conversion": f"urn:lla:llaPartnerConversion:{conversion_id}",
        "conversionHappenedAt": happened_at_ms,
        "user": {"userIds": [{"idType": "SHA256_EMAIL", "idValue": hashed}]},
    }
    if amount_cents:
        event["conversionValue"] = {"currencyCode": currency.upper(), "amount": f"{amount_cents / 100:.2f}"}
    if event_id:
        event["eventId"] = event_id  # dedupes webhook retries
    return event


def _send(event: dict) -> None:
    """Blocking send. Runs on a background thread via track_subscription_purchase()."""
    try:
        resp = httpx.post(
            _ENDPOINT,
            headers={
                "Authorization": f"Bearer {_token()}",
                "LinkedIn-Version": _api_version(),
                "X-Restli-Protocol-Version": "2.0.0",
            },
            json=event,
            timeout=10.0,
        )
        if resp.status_code >= 300:
            logger.warning("LinkedIn CAPI send failed (%s): %s", resp.status_code, resp.text[:300])
    except Exception as e:  # noqa: BLE001 - conversions are best-effort
        logger.warning("LinkedIn CAPI send error (continuing): %s", e)


def track_subscription_purchase(
    email: str | None, event_id: str | None, amount_cents: int | None, currency: str | None = None
) -> None:
    """Fire-and-forget purchase conversion. No-op without token, conversion ID or email."""
    conversion_id = _purchase_conversion_id()
    if not (_token() and conversion_id and email):
        logger.info("LinkedIn CAPI disabled or no email; skip purchase conversion")
        return
    event = build_event(conversion_id, email, event_id, int(time.time() * 1000), amount_cents, currency or "usd")
    threading.Thread(target=_send, args=(event,), daemon=True).start()
