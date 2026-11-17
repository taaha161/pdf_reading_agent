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


def _send(subject: str, text: str, reply_to: str | None = None) -> None:
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
                **({"reply_to": reply_to} if reply_to else {}),
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


def notify_feedback(
    rating: int | None,
    comment: str | None,
    user_id: str | None,
    contact_ok: bool,
    *,
    email: str | None = None,
    name: str | None = None,
    job_id: str | None = None,
    via_job_link: bool = False,
) -> None:
    """Feedback lands in the team inbox; Reply goes straight to the customer when known."""
    score = f"{rating}/5" if rating else "no rating"
    who = email or "anonymous"
    if email and via_job_link:
        who += " (matched via job link, not logged in)"
    lines = [
        f"Rating: {score}",
        f"Comment: {comment or 'n/a'}",
        "",
        f"From: {(name + ' <' + email + '>') if (name and email) else who}",
        f"User ID: {user_id or 'anonymous'}",
        f"Job: {job_id or 'n/a'}",
        f"OK to contact: {'yes' if contact_ok else 'no'}",
    ]
    if email:
        lines += ["", "Reply to this email to answer them directly."]
    subject = f"Feedback {score}" + (f" from {email}" if email else "")
    threading.Thread(target=_send, args=(subject, "\n".join(lines), email), daemon=True).start()


def _notify(subject: str, text: str) -> None:
    """Fire-and-forget: dispatch the email on a daemon thread."""
    threading.Thread(target=_send, args=(subject, text), daemon=True).start()


def notify_team(subject: str, text: str) -> None:
    """Fire-and-forget email to the team inbox (NOTIFY_EMAIL_TO)."""
    _notify(subject, text)


_PAID_WELCOME_TEXT = """Welcome to Bank Statement Scanner!

Your Monthly plan is active: {pages} pages every month.

If you haven't set your password yet, set it here to log in:
{link}

(Signed up with Google using this same email? You can also just use "Continue with Google".)

Questions? Just reply to this email.

The Bank Statement Scanner team
"""

_PAID_WELCOME_HTML = """<div style="font-family:Inter,-apple-system,'Segoe UI',Roboto,Arial,sans-serif;max-width:520px;margin:0 auto;color:#0f172a">
<h1 style="font-size:22px;margin:0 0 12px">You're subscribed &#10003;</h1>
<p style="font-size:15px;line-height:1.6;color:#334155;margin:0 0 16px">Your Monthly plan is active: <strong>{pages} pages every month</strong>.</p>
<p style="font-size:15px;line-height:1.6;color:#334155;margin:0 0 20px">If you haven't set your password yet, set it now to log in to your account.</p>
<p style="margin:0 0 24px"><a href="{link}" style="display:inline-block;padding:12px 22px;background:#2563eb;color:#fff;border-radius:10px;font-weight:600;text-decoration:none">Set your password</a></p>
<p style="font-size:13px;line-height:1.6;color:#64748b;margin:0">Signed up with Google using this email? You can also use &ldquo;Continue with Google&rdquo;. Questions? Just reply to this email.</p>
</div>"""


def send_paid_welcome_email(to: str, link: str, pages: int = 100) -> None:
    """Fire-and-forget welcome for a paid signup, with a set-password link."""

    def _go() -> None:
        key = _api_key()
        if not key:
            logger.info("RESEND_API_KEY not set; skip paid welcome email")
            return
        try:
            resp = httpx.post(
                _RESEND_ENDPOINT,
                headers={"Authorization": f"Bearer {key}"},
                json={
                    "from": _from_addr(),
                    "to": [to],
                    "reply_to": _to_addr(),
                    "subject": "You're subscribed: set your password",
                    "text": _PAID_WELCOME_TEXT.format(pages=pages, link=link),
                    "html": _PAID_WELCOME_HTML.format(pages=pages, link=link),
                },
                timeout=10.0,
            )
            if resp.status_code >= 300:
                logger.warning("paid welcome email failed (%s): %s", resp.status_code, resp.text[:300])
        except Exception as e:  # noqa: BLE001
            logger.warning("paid welcome email error (continuing): %s", e)

    threading.Thread(target=_go, daemon=True).start()


def name_from_metadata(meta: dict | None) -> str | None:
    """Display name from Supabase user metadata (email signup: full_name; Google: full_name/name)."""
    if not isinstance(meta, dict):
        return None
    for key in ("full_name", "name"):
        val = meta.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return None


def _user_lines(email: str | None, user_id: str | None, name: str | None, referral_code: str | None) -> str:
    return (
        f"Name: {name or 'n/a'}\n"
        f"Email: {email or 'n/a'}\n"
        f"Referral code: {referral_code or 'none'}\n"
        f"User ID: {user_id or 'n/a'}"
    )


def notify_signup(email: str | None, user_id: str | None = None, *,
                  name: str | None = None, referral_code: str | None = None) -> None:
    who = name or email or user_id or "unknown"
    _notify(
        f"New signup: {who}" + (f" (ref: {referral_code})" if referral_code else ""),
        "A new user signed up.\n\n" + _user_lines(email, user_id, name, referral_code),
    )


def notify_login(email: str | None, user_id: str | None = None, *,
                 name: str | None = None, referral_code: str | None = None) -> None:
    who = name or email or user_id or "unknown"
    _notify(
        f"User login: {who}",
        "A user logged in.\n\n" + _user_lines(email, user_id, name, referral_code),
    )


def notify_scan(
    *,
    email: str | None,
    user_id: str | None,
    is_trial: bool,
    name: str | None = None,
    transaction_count: int,
    conversion_mode: str,
    filename: str | None = None,
) -> None:
    who = "anonymous trial" if is_trial else (name or email or user_id or "unknown")
    _notify(
        f"PDF scanned: {who}",
        (
            "A PDF was scanned.\n\n"
            f"User: {'anonymous trial' if is_trial else (name or 'n/a')}\n"
            f"Email: {'n/a' if is_trial else (email or 'n/a')}\n"
            f"User ID: {user_id or 'n/a'}\n"
            f"File: {filename or 'n/a'}\n"
            f"Transactions: {transaction_count}\n"
            f"Mode: {conversion_mode}"
        ),
    )
