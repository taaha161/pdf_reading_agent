"""Error monitoring (Sentry). Disabled unless SENTRY_DSN is set.

Privacy rules, because requests carry bank statements:
- never send request bodies (uploaded PDFs, form fields) or stack-frame locals
  (raw statement text and transactions live in local variables);
- no IPs, cookies or auth headers (send_default_pii=False, headers scrubbed);
- redact filenames in log messages/breadcrumbs (they often contain names or
  account numbers);
- identify users by Supabase user id only, never email.
"""
from __future__ import annotations

import logging
import os
import re
from typing import Any

logger = logging.getLogger("monitoring")

# "filename=Moniepoint MFB 8151183521 (Apr 2024 - Apr 2026).pdf, size=..." -> "filename=[redacted], size=..."
_FILENAME_RE = re.compile(r"(filename|file)=([^,]*?\.pdf|[^,\s]+)", re.IGNORECASE)
_SENSITIVE_HEADERS = {"authorization", "cookie", "set-cookie", "x-api-key", "cf-connecting-ip", "x-forwarded-for", "x-real-ip"}

_enabled = False

# main.py logs uncaught request exceptions here; the FastAPI integration already captures them.
UNCAUGHT_LOGGER = "pdf_processor_app.uncaught"


def redact(text: Any) -> Any:
    if not isinstance(text, str):
        return text
    return _FILENAME_RE.sub(lambda m: f"{m.group(1)}=[redacted]", text)


def _scrub_request(request: dict[str, Any]) -> None:
    request.pop("data", None)
    request.pop("cookies", None)
    headers = request.get("headers")
    if isinstance(headers, dict):
        for k in list(headers):
            if k.lower() in _SENSITIVE_HEADERS:
                headers[k] = "[redacted]"


def _scrub_logentry(entry: dict[str, Any] | None) -> None:
    if not entry:
        return
    if "message" in entry:
        entry["message"] = redact(entry["message"])
    if "formatted" in entry:
        entry["formatted"] = redact(entry["formatted"])
    params = entry.get("params")
    if isinstance(params, (list, tuple)):
        entry["params"] = [redact(p) for p in params]


def before_send(event: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any] | None:
    if isinstance(event.get("request"), dict):
        _scrub_request(event["request"])
    _scrub_logentry(event.get("logentry"))
    if "message" in event:
        event["message"] = redact(event["message"])
    for exc in (event.get("exception") or {}).get("values") or []:
        exc["value"] = redact(exc.get("value"))
        for frame in (exc.get("stacktrace") or {}).get("frames") or []:
            frame.pop("vars", None)
    for crumb in (event.get("breadcrumbs") or {}).get("values") or []:
        before_breadcrumb(crumb, {})
    return event


def before_breadcrumb(crumb: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any] | None:
    if "message" in crumb:
        crumb["message"] = redact(crumb["message"])
    data = crumb.get("data")
    if isinstance(data, dict):
        for k in list(data):
            data[k] = redact(data[k])
    return crumb


def init_monitoring() -> bool:
    """Initialise Sentry if SENTRY_DSN is set. Safe to call once at startup."""
    global _enabled
    dsn = os.environ.get("SENTRY_DSN", "").strip()
    if not dsn:
        return False
    import sentry_sdk
    from sentry_sdk.integrations.logging import LoggingIntegration, ignore_logger

    production = os.environ.get("PRODUCTION", "").strip().lower() in ("1", "true", "yes")
    sentry_sdk.init(
        dsn=dsn,
        environment=os.environ.get("SENTRY_ENVIRONMENT") or ("production" if production else "development"),
        release=os.environ.get("RENDER_GIT_COMMIT") or None,
        send_default_pii=False,
        include_local_variables=False,
        max_request_body_size="never",
        traces_sample_rate=float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0") or 0),
        integrations=[LoggingIntegration(level=logging.INFO, event_level=logging.ERROR)],
        before_send=before_send,
        before_breadcrumb=before_breadcrumb,
    )
    ignore_logger(UNCAUGHT_LOGGER)
    _enabled = True
    logger.info("monitoring: Sentry enabled")
    return True


def set_user(user_id: str | None) -> None:
    """Attach the Supabase user id (no email/IP) to events from the current scope."""
    if not _enabled or not user_id:
        return
    import sentry_sdk

    sentry_sdk.set_user({"id": user_id})


def capture_message(message: str, level: str = "warning", **tags: Any) -> None:
    """Report a handled-but-notable failure (e.g. a scan that failed for the user)."""
    if not _enabled:
        return
    import sentry_sdk

    with sentry_sdk.new_scope() as scope:
        for k, v in tags.items():
            if v is not None:
                scope.set_tag(k, v)
        sentry_sdk.capture_message(message, level=level)
