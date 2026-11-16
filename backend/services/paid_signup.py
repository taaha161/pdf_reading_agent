"""Paid signup: pay first (Stripe Checkout, no account yet), then create the account.

Flow
  1. Pricing "Get Monthly" -> create_guest_checkout(): subscription Checkout with no
     customer; Stripe collects the email. A referral code becomes the affiliate coupon.
  2. Stripe redirects to /welcome?session_id=...; session_status() confirms payment and
     makes sure the account exists, then the page lets the buyer set a password once.
  3. Webhooks (checkout.session.completed, invoice paid, subscription updated) also call
     ensure_account(), because Stripe doesn't guarantee event order or that the buyer
     ever opens /welcome. Everything here is idempotent.

Accounts created here carry user_metadata.paid_signup_customer = <Stripe customer id>.
That marker is the only thing that lets a checkout session set a password: Stripe does
not verify the email the buyer typed, so a session may never set a password on an
account it didn't create (e.g. someone else's existing account with that email).
"""
import logging
import os
import re
from datetime import datetime, timedelta, timezone

import httpx
import stripe
from stripe import StripeError

from services import billing
from services.affiliates import claim_referral, normalize_code, valid_code
from services.notifications import notify_signup, notify_team, send_paid_welcome_email
from store import get_affiliate_by_code, get_auth_user, get_billing, get_user_id_by_stripe_customer_id, mark_free_grant_used, set_stripe_ids

logger = logging.getLogger("pdf_processor_app.paid_signup")

FLOW = "paid_signup"
# The welcome page may set the first password only this long after the account was created.
PASSWORD_WINDOW = timedelta(hours=24)
PASSWORD_MIN_LENGTH = 8


def _supabase() -> tuple[str, str]:
    url = (os.environ.get("SUPABASE_URL", "").strip()).rstrip("/")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    return url, key


def _admin(method: str, path: str, json: dict) -> httpx.Response:
    url, key = _supabase()
    if not url or not key:
        raise RuntimeError("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set")
    return httpx.request(
        method,
        f"{url}/auth/v1/admin/{path}",
        headers={"Authorization": f"Bearer {key}", "apikey": key},
        json=json,
        timeout=10.0,
    )


# --- 1. Checkout ---------------------------------------------------------------------

def _guest_discount(code: str | None) -> dict | None:
    """Affiliate discount for a code, in the shape billing._referral_coupon_id expects."""
    code = normalize_code(code)
    if not valid_code(code):
        return None
    try:
        aff = get_affiliate_by_code(code)
    except Exception as e:  # noqa: BLE001 - a lookup failure must not block checkout
        logger.warning("guest checkout: affiliate lookup failed (continuing): %s", e)
        return None
    if not aff or not aff.get("active") or not float(aff.get("discount_pct") or 0) > 0:
        return None
    return {
        "affiliate_id": str(aff["id"]),
        "code": code,
        "pct": float(aff["discount_pct"]),
        "months": aff.get("discount_months"),
        "stripe_coupon_id": aff.get("stripe_coupon_id"),
    }


def create_guest_checkout(
    referral_code: str | None = None,
    ga_client_id: str | None = None,
    ga_session_id: str | None = None,
    ad_opt_out: bool = False,
) -> dict | None:
    """Subscription Checkout for someone without an account. Returns {url, sessionId} or None."""
    if not billing._stripe_available():
        logger.warning("Stripe not configured; cannot create guest checkout")
        return None
    stripe.api_key = billing._STRIPE_KEY
    meta = {"flow": FLOW}
    meta.update({k: str(v)[:64] for k, v in (("ga_client_id", ga_client_id), ("ga_session_id", ga_session_id)) if v})
    if ad_opt_out:
        meta["ad_opt_out"] = "1"
    promo: dict = {"allow_promotion_codes": True}
    discount = _guest_discount(referral_code)
    if discount:
        coupon_id = billing._referral_coupon_id(discount)
        if coupon_id:
            promo = {"discounts": [{"coupon": coupon_id}]}
            meta["referral_code"] = discount["code"]
    app = billing._FRONTEND_URL
    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": billing._PRICE_ID_MONTHLY, "quantity": 1}],
            success_url=f"{app}/welcome?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{app}/?checkout=cancelled#pricing",
            subscription_data={"metadata": dict(meta)},
            metadata=meta,
            **promo,
        )
    except StripeError as e:
        logger.exception("Guest checkout create failed: %s", e)
        return None
    return {"url": session.url, "sessionId": session.id}


# --- 2. Account ----------------------------------------------------------------------

def ensure_account(customer_id: str, email: str | None = None, referral_code: str | None = None,
                   name: str | None = None) -> dict | None:
    """Make sure the paying Stripe customer has an account; link it. Idempotent.

    Returns {"user_id", "created_here", "existing_account"} or None if it can't
    (no email yet / Supabase unavailable; the next webhook or page poll retries).
      created_here: this customer's checkout created the account (may set its password).
      existing_account: the email already had an account; the subscription is attached to it.
    """
    if not customer_id:
        return None
    user_id = get_user_id_by_stripe_customer_id(customer_id)
    user = get_auth_user(user_id=user_id) if user_id else None
    if not user:
        if not email:
            try:
                stripe.api_key = billing._STRIPE_KEY
                email = stripe.Customer.retrieve(customer_id).get("email")
            except StripeError as e:
                logger.warning("paid signup: customer %s lookup failed: %s", customer_id, e)
                return None
        if not email:
            return None
        user = get_auth_user(email=email) or _create_user(email, customer_id, name, referral_code)
        if not user:
            return None
        _link_customer(user, customer_id)

    created_here = user.get("paid_signup_customer") == customer_id
    if created_here:
        # Re-runnable, so a crash between steps is repaired by the next event.
        mark_free_grant_used(user["id"])
        if referral_code:
            try:
                claim_referral(user["id"], referral_code)
            except Exception as e:  # noqa: BLE001
                logger.warning("paid signup: referral claim failed (continuing): %s", e)
    return {"user_id": user["id"], "created_here": created_here, "existing_account": not created_here}


def _create_user(email: str, customer_id: str, name: str | None,
                 referral_code: str | None = None) -> dict | None:
    """Create the confirmed Supabase account for a paid signup (or find it if a racing call won)."""
    meta = {"signup_flow": FLOW, "paid_signup_customer": customer_id, "signup_plan": "subscription"}
    if name:
        meta["full_name"] = name.strip()[:120]
    try:
        r = _admin("POST", "users", {"email": email, "email_confirm": True, "user_metadata": meta})
    except Exception as e:  # noqa: BLE001
        logger.error("paid signup: create user failed: %s", e)
        return None
    if r.status_code < 300:
        user = get_auth_user(user_id=r.json().get("id"))
        if user:
            logger.info("paid signup: created user %s for customer %s", user["id"], customer_id)
            notify_signup(email, user["id"], name=(name or "").strip() or None,
                          referral_code=referral_code or None)
            _send_welcome(email)
        return user
    if r.status_code == 422:  # already registered: another event for this checkout got here first
        return get_auth_user(email=email)
    logger.error("paid signup: create user status=%s body=%s", r.status_code, r.text[:300])
    return None


def _link_customer(user: dict, customer_id: str) -> None:
    """Point the account at the paying customer. Flags a second subscription for the team."""
    billing_row = get_billing(user["id"]) or {}
    old_customer = billing_row.get("stripe_customer_id")
    if old_customer and old_customer != customer_id and billing_row.get("stripe_subscription_id"):
        logger.warning("paid signup: %s already subscribed (%s); new customer %s", user["id"], old_customer, customer_id)
        notify_team(
            f"Possible duplicate subscription: {user.get('email')}",
            f"{user.get('email')} paid through the pricing-page checkout but already had a subscription.\n\n"
            f"User: {user['id']}\nPrevious Stripe customer: {old_customer}\nNew Stripe customer: {customer_id}\n\n"
            "Check Stripe and refund/cancel one of them if it's a duplicate.",
        )
    set_stripe_ids(user["id"], customer_id, None)


def _send_welcome(email: str) -> None:
    """Email a set-password link, for buyers who close the tab before /welcome."""
    try:
        r = _admin("POST", "generate_link", {
            "type": "recovery",
            "email": email,
            "redirect_to": f"{billing._FRONTEND_URL}/reset-password",
        })
        body = r.json() if r.status_code < 300 else {}
        link = body.get("action_link") or (body.get("properties") or {}).get("action_link")
    except Exception as e:  # noqa: BLE001
        logger.warning("paid signup: set-password link failed: %s", e)
        link = None
    send_paid_welcome_email(email, link or f"{billing._FRONTEND_URL}/forgot-password")


# --- 3. Welcome page -----------------------------------------------------------------

def _paid_session(session_id: str):
    """The Checkout Session if it's a completed, paid paid-signup session, else None."""
    if not session_id or not session_id.startswith("cs_"):
        return None
    stripe.api_key = billing._STRIPE_KEY
    try:
        s = stripe.checkout.Session.retrieve(session_id)
    except StripeError as e:
        logger.info("welcome: session lookup failed: %s", e)
        return None
    if (s.get("metadata") or {}).get("flow") != FLOW:
        return None
    return s


def _session_paid(s) -> bool:
    return s.get("status") == "complete" and s.get("payment_status") in ("paid", "no_payment_required")


def _password_allowed(user: dict | None, customer_id: str) -> bool:
    if not user or user.get("paid_signup_customer") != customer_id or user.get("has_password"):
        return False
    created = user.get("created_at")
    return bool(created) and datetime.now(timezone.utc) - created < PASSWORD_WINDOW


def session_status(session_id: str) -> dict:
    """What /welcome shows. {"status": "invalid" | "pending" | "ready", ...}."""
    s = _paid_session(session_id)
    if not s:
        return {"status": "invalid"}
    if not _session_paid(s):
        return {"status": "pending"}
    details = s.get("customer_details") or {}
    email = details.get("email")
    acct = ensure_account(
        s.get("customer"), email, (s.get("metadata") or {}).get("referral_code"), details.get("name")
    )
    if not acct:
        return {"status": "pending"}
    user = get_auth_user(user_id=acct["user_id"])
    ref = _guest_discount((s.get("metadata") or {}).get("referral_code"))
    discount = {"code": ref["code"], "pct": ref["pct"], "months": ref["months"]} if ref else None
    return {
        "status": "ready",
        "email": (user or {}).get("email") or email,
        "needs_password": _password_allowed(user, s.get("customer")),
        "existing_account": acct["existing_account"],
        "amount_total": s.get("amount_total"),
        "currency": s.get("currency"),
        "discount": discount,
    }


def password_problem(password: str) -> str | None:
    """Same rules as the signup form. None if OK, else what's missing."""
    if not password or len(password) < PASSWORD_MIN_LENGTH:
        return f"At least {PASSWORD_MIN_LENGTH} characters"
    for pattern, msg in (("[A-Z]", "One uppercase letter"), ("[a-z]", "One lowercase letter"),
                         ("[0-9]", "One number"), ("[^A-Za-z0-9]", "One special character")):
        if not re.search(pattern, password):
            return msg
    return None


class PasswordError(Exception):
    """User-facing reason the password couldn't be set."""


def set_initial_password(session_id: str, password: str) -> str:
    """Set the first password on the account this paid checkout created. Returns the email."""
    problem = password_problem(password)
    if problem:
        raise PasswordError(f"Password must have: {problem}")
    s = _paid_session(session_id)
    if not s or not _session_paid(s):
        raise PasswordError("We couldn't find that payment.")
    acct = ensure_account(s.get("customer"), (s.get("customer_details") or {}).get("email"))
    user = get_auth_user(user_id=acct["user_id"]) if acct else None
    if not _password_allowed(user, s.get("customer")):
        raise PasswordError("This account already has a password. Log in instead.")
    try:
        r = _admin("PUT", f"users/{user['id']}", {"password": password})
    except Exception as e:  # noqa: BLE001
        logger.error("welcome: set password failed: %s", e)
        raise PasswordError("Couldn't save your password. Please try again.") from e
    if r.status_code >= 300:
        logger.error("welcome: set password status=%s body=%s", r.status_code, r.text[:300])
        raise PasswordError("Couldn't save your password. Please try again.")
    return user["email"]
