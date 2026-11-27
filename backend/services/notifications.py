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
import html
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


def _trustpilot_bcc() -> list[str]:
    """Trustpilot's invite address (TRUSTPILOT_BCC). A customer email BCC'd to it makes Trustpilot
    send that customer a review invitation (no incentive attached). Unset = no BCC."""
    addr = os.environ.get("TRUSTPILOT_BCC", "").strip()
    return [addr] if addr else []


def _bcc_field() -> dict:
    bcc = _trustpilot_bcc()
    return {"bcc": bcc} if bcc else {}


def _customer_to(email: str, name: str | None = None) -> str:
    """'Name <email>' so Trustpilot's invitation can greet the customer by name."""
    clean = (name or "").replace('"', "").replace("<", "").replace(">", "").strip()
    return f'"{clean}" <{email}>' if clean else email


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
                **_bcc_field(),
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
                    **_bcc_field(),
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


CHECKIN_AFTER_SCANS = 3
_G2_REVIEW_URL = "https://www.g2.com/products/bank-statement-scanner/take_survey"
_TRUSTPILOT_REVIEW_URL = "https://www.trustpilot.com/evaluate/bankstatementscanner.com"
_SUPPORT_PHONE = "+1 (847) 834-4295"

_CHECKIN_TEXT = """Hi {first},

You've converted {scans} statements with Bank Statement Scanner so far. Quick check-in: is everything coming out right?

If a bank's layout gave you trouble or a balance didn't match, reply and tell us which bank. We read every reply.

If it's been useful, a short G2 review helps a lot. We'll add 100 pages to your account for any honest review, good or bad. They never expire.
Write a G2 review: {g2}
Then click "Already reviewed us on G2?" in the app, or reply with the link.

Prefer Trustpilot? We'd love a review there too: {trustpilot}
(Trustpilot doesn't allow rewards for reviews, so that one doesn't earn pages. You may also get a short invite email from Trustpilot.)

{support}
{phone}

Best regards,
The Bank Statement Scanner Team
https://bankstatementscanner.com
"""

_P = '<p style="margin:0 0 16px;font-size:16px;line-height:1.6;">{}</p>'

_CHECKIN_HTML = """<!doctype html><html><body style="margin:0;padding:0;background:#f4f6fb;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#1f2937;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6fb;padding:32px 16px;"><tr><td align="center">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;background:#ffffff;border-radius:14px;overflow:hidden;box-shadow:0 2px 10px rgba(16,24,40,.06);">
  <tr><td style="background:#1e3a8a;padding:22px 32px;"><span style="color:#ffffff;font-size:18px;font-weight:700;letter-spacing:.2px;">Bank Statement Scanner</span></td></tr>
  <tr><td style="padding:32px 32px 8px;">{body}</td></tr>
  <tr><td align="center" style="padding:4px 32px 24px;"><a href="{g2}" style="display:inline-block;background:#1e3a8a;color:#ffffff;text-decoration:none;font-weight:600;font-size:15px;padding:12px 24px;border-radius:8px;">Write a G2 review</a></td></tr>
  <tr><td style="padding:0 32px 8px;">
    <p style="margin:0 0 16px;font-size:14px;line-height:1.6;color:#374151;">Then click &ldquo;Already reviewed us on G2?&rdquo; in the app, or reply with the link.</p>
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f0fdf6;border-left:4px solid #00b67a;border-radius:8px;margin:0 0 20px;"><tr><td style="padding:14px 18px;font-size:14px;line-height:1.6;color:#374151;">
      <strong style="color:#065f46;">Prefer Trustpilot?</strong> We&rsquo;d love a review there too: <a href="{trustpilot}" style="color:#047857;font-weight:600;">Review us on Trustpilot &rarr;</a><br>
      <span style="font-size:12px;color:#6b7280;">Trustpilot doesn&rsquo;t allow rewards for reviews, so that one doesn&rsquo;t earn pages. You may also get a short invite email from Trustpilot.</span>
    </td></tr></table>
    <p style="margin:0 0 6px;font-size:15px;line-height:1.6;">&#9993;&nbsp; <a href="mailto:{support}" style="color:#1e3a8a;text-decoration:none;font-weight:600;">{support}</a></p>
    <p style="margin:0 0 20px;font-size:15px;line-height:1.6;">&#9742;&nbsp; <a href="tel:+18478344295" style="color:#1e3a8a;text-decoration:none;font-weight:600;">{phone}</a></p>
    <p style="margin:16px 0 28px;font-size:16px;line-height:1.6;">Best regards,<br><strong>The Bank Statement Scanner Team</strong></p>
  </td></tr>
  <tr><td style="background:#f9fafb;padding:16px 32px;border-top:1px solid #eef0f4;font-size:12px;color:#9ca3af;text-align:center;"><a href="https://bankstatementscanner.com" style="color:#9ca3af;">bankstatementscanner.com</a></td></tr>
</table></td></tr></table></body></html>"""


def _first_name(name: str | None) -> str:
    first = (name or "").strip().split(" ")[0] if name else ""
    return first or "there"


def send_checkin_email(to: str, name: str | None, scans: int) -> None:
    """Fire-and-forget check-in after a user's 3rd scan: ask for problems, offer the G2 review
    reward, and BCC Trustpilot so it sends its own (unrewarded) review invitation."""
    first = _first_name(name)
    support = _to_addr()
    body = "".join(_P.format(t) for t in [
        f"Hi {html.escape(first)},",
        f"You've converted {scans} statements with Bank Statement Scanner so far. Quick check-in: is everything coming out right?",
        "If a bank's layout gave you trouble or a balance didn't match, reply and tell us which bank. We read every reply.",
        "If it's been useful, a short G2 review helps a lot. We'll add 100 pages to your account for any honest review, good or bad. They never expire.",
    ])

    def _go() -> None:
        key = _api_key()
        if not key:
            logger.info("RESEND_API_KEY not set; skip check-in email")
            return
        try:
            resp = httpx.post(
                _RESEND_ENDPOINT,
                headers={"Authorization": f"Bearer {key}"},
                json={
                    "from": _from_addr(),
                    "to": [_customer_to(to, name)],
                    "reply_to": support,
                    **_bcc_field(),
                    "subject": "How's Bank Statement Scanner working for you?",
                    "text": _CHECKIN_TEXT.format(first=first, scans=scans, g2=_G2_REVIEW_URL, trustpilot=_TRUSTPILOT_REVIEW_URL, support=support, phone=_SUPPORT_PHONE),
                    "html": _CHECKIN_HTML.format(body=body, g2=_G2_REVIEW_URL, trustpilot=_TRUSTPILOT_REVIEW_URL, support=support, phone=_SUPPORT_PHONE),
                    "tags": [{"name": "category", "value": "checkin"}],
                },
                timeout=10.0,
            )
            if resp.status_code >= 300:
                logger.warning("check-in email failed (%s): %s", resp.status_code, resp.text[:300])
        except Exception as e:  # noqa: BLE001
            logger.warning("check-in email error (continuing): %s", e)

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
    reconciliation: dict | None = None,
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
            f"Mode: {conversion_mode}\n"
            f"Reconciliation: {_reconciliation_line(reconciliation)}"
        ),
    )


def _reconciliation_line(reconciliation: dict | None) -> str:
    """One line for the owner alert, so extraction mismatches are visible without a complaint."""
    if not reconciliation:
        return "n/a"
    status = reconciliation.get("status", "n/a")
    if status == "mismatch":
        diffs = [c.get("difference") for c in reconciliation.get("checks", []) if c.get("status") == "fail"]
        return f"MISMATCH (off by {', '.join(f'{d:.2f}' for d in diffs if d is not None) or '?'})"
    if status == "unverified":
        return f"unverified ({reconciliation.get('reason') or 'no reason'})"
    return status
