"""GA4 Measurement Protocol: server-side `subscribe` and `purchase` events.

Payments happen in Stripe, not in the browser, so the Stripe webhook reports them
to GA4 directly. The browser's GA client id and session id are captured at
checkout (see frontend/src/lib/analytics.js) and stored in Stripe metadata, so
GA4 attributes the event to the same visitor and session that came from the ad.

Best-effort like linkedin_capi: every send runs on a daemon thread and swallows
all errors, so a GA4 outage never blocks or fails a Stripe webhook.

Env:
  GA4_API_SECRET       -- GA4 Admin > Data streams > Measurement Protocol API secrets
                          (if unset, events are silently disabled).
  GA4_MEASUREMENT_ID   -- web stream measurement id (default: G-75SRB0NNXY).
"""

import hashlib
import logging
import os
import threading

import httpx

logger = logging.getLogger("pdf_processor_app.ga4_mp")

_ENDPOINT = "https://www.google-analytics.com/mp/collect"
_DEFAULT_MEASUREMENT_ID = "G-75SRB0NNXY"
_MAX_ID_LEN = 64


def _api_secret() -> str:
    return os.environ.get("GA4_API_SECRET", "").strip()


def _measurement_id() -> str:
    return os.environ.get("GA4_MEASUREMENT_ID", _DEFAULT_MEASUREMENT_ID).strip()


def _clean(value) -> str:
    return str(value or "").strip()[:_MAX_ID_LEN]


def _fallback_client_id(user_id: str) -> str:
    """Stable GA-style client id when the browser's was not captured (event stays unattributed)."""
    digest = int(hashlib.sha256(user_id.encode()).hexdigest()[:16], 16)
    return f"{digest % 10**10}.{digest % 10**9 + 10**9}"


def build_payload(
    user_id: str,
    event_name: str,
    params: dict,
    ga_client_id: str | None = None,
    ga_session_id: str | None = None,
) -> dict:
    client_id = _clean(ga_client_id) or _fallback_client_id(user_id)
    event_params = {k: v for k, v in params.items() if v is not None}
    session_id = _clean(ga_session_id)
    if session_id.isdigit():
        event_params["session_id"] = int(session_id)
        event_params["engagement_time_msec"] = 1
    return {
        "client_id": client_id,
        "user_id": user_id,
        "events": [{"name": event_name, "params": event_params}],
    }


def _send(payload: dict) -> None:
    try:
        resp = httpx.post(
            _ENDPOINT,
            params={"measurement_id": _measurement_id(), "api_secret": _api_secret()},
            json=payload,
            timeout=10.0,
        )
        if resp.status_code >= 300:
            logger.warning("GA4 MP send failed (%s): %s", resp.status_code, resp.text[:300])
    except Exception as e:  # noqa: BLE001 - analytics are best-effort
        logger.warning("GA4 MP send error (continuing): %s", e)


def track_event(
    user_id: str | None,
    event_name: str,
    params: dict,
    ga_client_id: str | None = None,
    ga_session_id: str | None = None,
) -> None:
    """Fire-and-forget GA4 event. No-op without API secret or user id."""
    if not (_api_secret() and user_id):
        logger.info("GA4 MP disabled or no user; skip %s", event_name)
        return
    payload = build_payload(user_id, event_name, params, ga_client_id, ga_session_id)
    threading.Thread(target=_send, args=(payload,), daemon=True).start()


def ga_ids_from_metadata(metadata: dict | None) -> tuple[str | None, str | None]:
    metadata = metadata or {}
    return metadata.get("ga_client_id") or None, metadata.get("ga_session_id") or None
