"""Emails via Resend: owner notifications and user spreadsheet emails.

Owner notifications: a best-effort email to the site owner when a user signs
up, logs in, or scans a PDF. Every send is fire-and-forget on a daemon thread and swallows all
errors: notifications must never block or fail a user request.

Env:
  RESEND_API_KEY   -- Resend API key (if unset, notifications are silently disabled).
  NOTIFY_EMAIL_TO  -- recipient (default: team@bankstatementscanner.com).
  NOTIFY_EMAIL_FROM-- verified sender (default: BankStatementScanner
                      <notifications@bankstatementscanner.com>).
"""

import base64
import logging
import os
import threading

import httpx

logger = logging.getLogger("pdf_processor_app.notifications")

_RESEND_ENDPOINT = "https://api.resend.com/emails"


def _api_key() -> str:
    return os.environ.get("RESEND_API_KEY", "").strip()


def _to_addr() -> str:
    return os.environ.get("NOTIFY_EMAIL_TO", "team@bankstatementscanner.com").strip()


def _from_addr() -> str:
    return os.environ.get(
        "NOTIFY_EMAIL_FROM",
        "BankStatementScanner <notifications@bankstatementscanner.com>",
    ).strip()


def _send(subject: str, text: str) -> None:
    """Blocking send. Runs on a background thread via notify()."""
    key = _api_key()
    if not key:
        logger.info("notifications disabled (RESEND_API_KEY not set); skip: %s", subject)
        return
    try:
        resp = httpx.post(
            _RESEND_ENDPOINT,
            headers={"Authorization": f"Bearer {key}"},
            json={
                "from": _from_addr(),
                "to": [_to_addr()],
                "subject": subject,
                "text": text,
            },
            timeout=10.0,
        )
        if resp.status_code >= 300:
            logger.warning("Resend send failed (%s): %s", resp.status_code, resp.text[:300])
    except Exception as e:  # noqa: BLE001 - notifications are best-effort
        logger.warning("Resend send error (continuing): %s", e)


def _app_url() -> str:
    return (os.environ.get("FRONTEND_URL") or "https://bankstatementscanner.com").strip().rstrip("/")


_SPREADSHEET_EMAIL_TEXT = """Hi,

Your converted bank statement is attached ({filename}). It opens directly in Excel, Google Sheets or Numbers.

Want to keep a history of your statements, merge months together, or convert more? Create a free account:
{signup_url}

Quick question: what are you using your statements for (taxes, bookkeeping, a loan application...)? Just hit reply. I read every email.

Taaha
Founder, BankStatementScanner
"""


def send_spreadsheet_email(to: str, content: bytes, filename: str = "statement.csv") -> bool:
    """Email a converted statement (CSV or Excel) to a user. Blocking; returns True on success.

    Unlike owner notifications, the caller needs the result to tell the user
    whether the email went out.
    """
    key = _api_key()
    if not key:
        logger.warning("RESEND_API_KEY not set; cannot send spreadsheet email")
        return False
    try:
        resp = httpx.post(
            _RESEND_ENDPOINT,
            headers={"Authorization": f"Bearer {key}"},
            json={
                "from": _from_addr(),
                "to": [to],
                "reply_to": _to_addr(),
                "subject": "Your converted bank statement",
                "text": _SPREADSHEET_EMAIL_TEXT.format(filename=filename, signup_url=f"{_app_url()}/signup"),
                "attachments": [
                    {
                        "filename": filename,
                        "content": base64.b64encode(content).decode("ascii"),
                    }
                ],
                "tags": [{"name": "category", "value": "email_spreadsheet"}],
            },
            timeout=15.0,
        )
        if resp.status_code >= 300:
            logger.warning("Resend spreadsheet send failed (%s): %s", resp.status_code, resp.text[:300])
            return False
        return True
    except Exception as e:  # noqa: BLE001
        logger.warning("Resend spreadsheet send error: %s", e)
        return False


def notify_email_capture(email: str, marketing_opt_in: bool) -> None:
    _notify(
        f"Email captured: {email}",
        f"An anonymous user asked for their spreadsheet by email.\n\nEmail: {email}\nMarketing opt-in: {'yes' if marketing_opt_in else 'no'}",
    )


def _notify(subject: str, text: str) -> None:
    """Fire-and-forget: dispatch the email on a daemon thread."""
    threading.Thread(target=_send, args=(subject, text), daemon=True).start()


def notify_signup(email: str | None, user_id: str | None = None) -> None:
    who = email or user_id or "unknown"
    _notify(
        f"New signup: {who}",
        f"A new user signed up.\n\nEmail: {email or 'n/a'}\nUser ID: {user_id or 'n/a'}",
    )


def notify_login(email: str | None, user_id: str | None = None) -> None:
    who = email or user_id or "unknown"
    _notify(
        f"User login: {who}",
        f"A user logged in.\n\nEmail: {email or 'n/a'}\nUser ID: {user_id or 'n/a'}",
    )


def notify_scan(
    *,
    email: str | None,
    user_id: str | None,
    is_trial: bool,
    transaction_count: int,
    conversion_mode: str,
    filename: str | None = None,
) -> None:
    who = "anonymous trial" if is_trial else (email or user_id or "unknown")
    _notify(
        f"PDF scanned: {who}",
        (
            "A PDF was scanned.\n\n"
            f"User: {'anonymous trial' if is_trial else (email or 'n/a')}\n"
            f"User ID: {user_id or 'n/a'}\n"
            f"File: {filename or 'n/a'}\n"
            f"Transactions: {transaction_count}\n"
            f"Mode: {conversion_mode}"
        ),
    )
