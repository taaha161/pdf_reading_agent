"""Billing: cost map, Stripe customer/checkout, webhook handler."""
import logging
import os
from typing import Literal

import stripe
from stripe import StripeError

from store import add_balance, get_billing, get_user_id_by_stripe_customer_id, set_balance, set_stripe_ids

logger = logging.getLogger("pdf_processor_app.billing")

# Scan cost in cents: fast = 0.5¢, balanced = $1, accurate = $1.50
SCAN_COST_CENTS = {"fast": 0.5, "balanced": 100, "accurate": 150}

_STRIPE_KEY = os.environ.get("STRIPE_SECRET_KEY", "").strip()
_STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "").strip()
_PRICE_ID_MONTHLY = os.environ.get("STRIPE_PRICE_ID_MONTHLY", "").strip()
_PRICE_ID_TOPUP = os.environ.get("STRIPE_PRICE_ID_TOPUP", "").strip()
_FRONTEND_URL = (os.environ.get("FRONTEND_URL", "http://localhost:5173") or "http://localhost:5173").strip().rstrip("/")


def _stripe_available() -> bool:
    return bool(_STRIPE_KEY and _PRICE_ID_MONTHLY and _PRICE_ID_TOPUP)


def get_or_create_stripe_customer(user_id: str, email: str | None) -> str | None:
    """Return stripe_customer_id for user; create Stripe Customer if needed. Saves to DB."""
    if not _STRIPE_KEY:
        return None
    stripe.api_key = _STRIPE_KEY
    row = get_billing(user_id)
    if row and row.get("stripe_customer_id"):
        return row["stripe_customer_id"]
    try:
        customer = stripe.Customer.create(
            metadata={"user_id": user_id},
            email=email or None,
        )
        set_stripe_ids(user_id, customer.id, None)
        return customer.id
    except StripeError as e:
        logger.exception("Stripe Customer create failed: %s", e)
        return None


def create_checkout_session(
    user_id: str,
    mode: Literal["subscription", "topup"],
    success_url: str | None = None,
    cancel_url: str | None = None,
    email: str | None = None,
) -> dict | None:
    """Create Stripe Checkout Session. Returns { 'url': str } or None on error."""
    if not _stripe_available():
        logger.warning("Stripe not configured; cannot create checkout session")
        return None
    stripe.api_key = _STRIPE_KEY
    success_url = success_url or f"{_FRONTEND_URL}/settings?checkout=success"
    cancel_url = cancel_url or f"{_FRONTEND_URL}/settings?checkout=cancelled"
    customer_id = get_or_create_stripe_customer(user_id, email)
    if not customer_id:
        return None
    try:
        if mode == "subscription":
            session = stripe.checkout.Session.create(
                customer=customer_id,
                mode="subscription",
                line_items=[{"price": _PRICE_ID_MONTHLY, "quantity": 1}],
                success_url=success_url,
                cancel_url=cancel_url,
                client_reference_id=user_id,
                subscription_data={"metadata": {"user_id": user_id}},
            )
        else:
            session = stripe.checkout.Session.create(
                customer=customer_id,
                mode="payment",
                line_items=[{"price": _PRICE_ID_TOPUP, "quantity": 1}],
                success_url=success_url,
                cancel_url=cancel_url,
                client_reference_id=user_id,
                metadata={"user_id": user_id, "topup": "1"},
            )
        return {"url": session.url, "sessionId": session.id}
    except StripeError as e:
        logger.exception("Stripe Checkout create failed: %s", e)
        return None


def handle_webhook(payload: bytes, signature: str) -> tuple[bool, str]:
    """Verify signature and process event. Returns (ok, message)."""
    if not _STRIPE_KEY or not _STRIPE_WEBHOOK_SECRET:
        return False, "Stripe webhook not configured"
    stripe.api_key = _STRIPE_KEY
    try:
        event = stripe.Webhook.construct_event(payload, signature, _STRIPE_WEBHOOK_SECRET)
    except ValueError as e:
        return False, f"Invalid payload: {e}"
    except stripe.SignatureVerificationError as e:
        return False, f"Invalid signature: {e}"

    if event.type == "invoice.payment_succeeded":
        return _handle_invoice_paid(event)
    if event.type == "customer.subscription.updated":
        return _handle_subscription_updated(event)
    if event.type == "customer.subscription.deleted":
        return _handle_subscription_deleted(event)
    return True, "Event ignored"


def _handle_invoice_paid(event) -> tuple[bool, str]:
    invoice = event["data"]["object"]
    billing_reason = invoice.get("billing_reason")
    customer_id = invoice.get("customer")
    subscription_id = invoice.get("subscription")
    if not customer_id:
        return True, "No customer"

    user_id = _user_id_from_customer(customer_id, subscription_id, invoice.get("client_reference_id"))
    if not user_id:
        return True, "Could not resolve user_id"

    amount_paid = invoice.get("amount_paid") or 0  # cents

    # Subscription cycle or create: set balance to $10 (1000 cents)
    if billing_reason in ("subscription_cycle", "subscription_create") and subscription_id:
        try:
            set_balance(user_id, 1000)
            set_stripe_ids(user_id, customer_id, subscription_id)
            return True, "Balance set to 1000"
        except Exception as e:
            logger.exception("set_balance failed: %s", e)
            return False, str(e)

    # One-time payment (top-up): no subscription on invoice
    if not subscription_id and amount_paid > 0:
        try:
            add_balance(user_id, amount_paid)
            return True, "Top-up applied"
        except Exception as e:
            logger.exception("add_balance failed: %s", e)
            return False, str(e)

    return True, "OK"


def _handle_subscription_updated(event) -> tuple[bool, str]:
    sub = event["data"]["object"]
    customer_id = sub.get("customer")
    user_id = _user_id_from_customer(customer_id, sub.get("id"), None)
    if user_id and sub.get("status") in ("active", "trialing"):
        set_stripe_ids(user_id, customer_id, sub.get("id"))
    return True, "OK"


def _handle_subscription_deleted(event) -> tuple[bool, str]:
    sub = event["data"]["object"]
    customer_id = sub.get("customer")
    user_id = _user_id_from_customer(customer_id, sub.get("id"), None)
    if user_id:
        set_stripe_ids(user_id, customer_id, None)
    return True, "OK"


def _user_id_from_customer(stripe_customer_id: str | None, subscription_id: str | None, client_reference_id: str | None) -> str | None:
    """Resolve user_id from client_reference_id or stripe_customer_id lookup."""
    if client_reference_id:
        return client_reference_id
    if stripe_customer_id:
        return get_user_id_by_stripe_customer_id(stripe_customer_id)
    return None
