"""Billing: cost map, Stripe customer/checkout, webhook handler."""
import logging
import os
from typing import Literal

import stripe
from stripe import StripeError

from services.affiliates import discounted_cents, user_discount
from services.affiliates import record_payment as record_affiliate_payment
from services.ga4_mp import ga_ids_from_metadata, track_event
from services.linkedin_capi import track_subscription_purchase
from store import add_pack_pages, clear_subscription, set_affiliate_coupon, get_billing, get_user_id_by_stripe_customer_id, set_plan_pages, set_stripe_ids

logger = logging.getLogger("pdf_processor_app.billing")

# --- Page pricing ---
# Billing unit is a PDF page, counted before any processing.
FREE_ANON_PAGES = 10  # without an account, per client IP (lifetime)
FREE_SIGNUP_PAGES = 100  # one-time grant on signup...
FREE_SIGNUP_DAYS = 30  # ...valid for the first 30 days
PLAN_PAGES = 150  # $10/month plan: pages per billing cycle (reset, no rollover)
PLAN_PRICE_CENTS = 1000
# Page packs: id -> (pages, price in cents). Pack pages never expire.
# Small add-on packs are for active subscribers only.
SUBSCRIBER_PACKS: dict[str, tuple[int, int]] = {
    "10": (10, 200),
    "30": (30, 500),
    "100": (100, 1000),
}
# Without a subscription, pages are only sold as this bulk pack.
BULK_PACK_ID = "450"
BULK_PACK: tuple[int, int] = (450, 4999)
PAGE_PACKS: dict[str, tuple[int, int]] = {**SUBSCRIBER_PACKS, BULK_PACK_ID: BULK_PACK}
DEFAULT_PACK = "30"  # subscribers; everyone else gets BULK_PACK_ID
# Pages charged per PDF page, by conversion mode.
MODE_PAGE_MULTIPLIER = {"fast": 1, "balanced": 1, "accurate": 2}
# Old $-credit top-ups still in flight at launch convert at $0.10/page.
_LEGACY_CENTS_PER_PAGE = 10


def scan_cost_pages(page_count: int, conversion_mode: str) -> int:
    """Pages charged for scanning a PDF with `page_count` pages in this mode."""
    return max(1, page_count) * MODE_PAGE_MULTIPLIER.get(conversion_mode, 1)

_STRIPE_KEY = os.environ.get("STRIPE_SECRET_KEY", "").strip()
_STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "").strip()
_PRICE_ID_MONTHLY = os.environ.get("STRIPE_PRICE_ID_MONTHLY", "").strip()
_FRONTEND_URL = (os.environ.get("FRONTEND_URL", "http://localhost:5173") or "http://localhost:5173").strip().rstrip("/")


# Ad-campaign offers, keyed by the code the landing page passes through signup.
# Value = free trial days on the monthly subscription. Server-side allowlist so
# a client can't invent its own discount.
OFFERS: dict[str, int] = {
    "linkedin1m": 30,  # LinkedIn paid-ad landing page (/lp/linkedin): first month free
}


def offer_trial_days(offer: str | None) -> int:
    """Trial days for a known offer code, else 0."""
    return OFFERS.get((offer or "").strip().lower(), 0)


def _has_had_subscription(customer_id: str) -> bool:
    """True if this Stripe customer ever had a subscription (any status).

    Offers are for first-time subscribers only. Fails closed (True) on Stripe
    errors so an outage never hands out a free month by accident.
    """
    try:
        subs = stripe.Subscription.list(customer=customer_id, status="all", limit=1)
        return bool(subs.data)
    except StripeError as e:
        logger.warning("Subscription history lookup failed; skipping offer: %s", e)
        return True


def _referral_coupon_id(discount: dict) -> str | None:
    """Stripe coupon for an affiliate's subscription discount; created once and cached on the affiliate."""
    if discount.get("stripe_coupon_id"):
        return discount["stripe_coupon_id"]
    months = discount.get("months")
    duration = {"duration": "repeating", "duration_in_months": months} if months else {"duration": "forever"}
    try:
        coupon = stripe.Coupon.create(
            percent_off=discount["pct"],
            name=f"Referral discount ({discount['code'].upper()})"[:40],
            metadata={"affiliate_id": discount["affiliate_id"], "code": discount["code"]},
            **duration,
        )
    except StripeError as e:
        logger.warning("Referral coupon create failed; checkout without discount: %s", e)
        return None
    set_affiliate_coupon(discount["affiliate_id"], coupon.id)
    return coupon.id


def _referral_discount(user_id: str) -> dict | None:
    """Never let a discount lookup failure block checkout."""
    try:
        return user_discount(user_id)
    except Exception as e:  # noqa: BLE001
        logger.warning("Referral discount lookup failed (continuing): %s", e)
        return None


def _stripe_available() -> bool:
    return bool(_STRIPE_KEY and _PRICE_ID_MONTHLY)


def get_or_create_stripe_customer(user_id: str, email: str | None) -> str | None:
    """Return stripe_customer_id for user; create Stripe Customer if needed. Saves to DB."""
    if not _STRIPE_KEY:
        return None
    stripe.api_key = _STRIPE_KEY
    row = get_billing(user_id)
    stored_id = row.get("stripe_customer_id") if row else None
    if stored_id:
        # Stored id can be stale (test-mode id, or deleted customer): verify, else recreate.
        try:
            existing = stripe.Customer.retrieve(stored_id)
            if not getattr(existing, "deleted", False):
                return stored_id
            logger.warning("Stripe customer %s deleted; recreating for user %s", stored_id, user_id)
        except stripe.InvalidRequestError as e:
            if getattr(e, "code", None) != "resource_missing":
                logger.exception("Stripe Customer retrieve failed: %s", e)
                return None
            logger.warning("Stripe customer %s missing; recreating for user %s", stored_id, user_id)
        except StripeError as e:
            logger.exception("Stripe Customer retrieve failed: %s", e)
            return None
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


class PackNotAllowed(Exception):
    """A subscriber-only pack was requested by a user without an active subscription."""


def resolve_pack(pack: str | None, subscribed: bool) -> str:
    """Pack id this user may buy. Raises PackNotAllowed for a subscriber pack without a subscription."""
    if subscribed:
        return pack if pack in PAGE_PACKS else DEFAULT_PACK
    if pack in SUBSCRIBER_PACKS:
        raise PackNotAllowed(pack)
    return BULK_PACK_ID


def _is_subscribed(user_id: str) -> bool:
    billing = get_billing(user_id)
    return bool(billing and billing.get("stripe_subscription_id"))


def create_checkout_session(
    user_id: str,
    mode: Literal["subscription", "topup"],
    success_url: str | None = None,
    cancel_url: str | None = None,
    email: str | None = None,
    offer: str | None = None,
    ga_client_id: str | None = None,
    ga_session_id: str | None = None,
    ad_opt_out: bool = False,
    pack: str | None = None,
) -> dict | None:
    """Create Stripe Checkout Session. Returns { 'url': str } or None on error.

    `offer` (subscription only): a code from OFFERS. Applied as a free trial
    when the customer has never subscribed before; silently ignored otherwise.
    `ga_client_id`/`ga_session_id`: the browser's GA4 ids, stored in Stripe metadata
    so webhook events (subscribe, purchase) attribute to the visitor's ad session.
    `pack` (topup only): a key of PAGE_PACKS. Subscribers may buy any pack (unknown
    values fall back to DEFAULT_PACK). Everyone else may only buy BULK_PACK_ID;
    asking for a subscriber pack raises PackNotAllowed.
    Referred users get their affiliate's discount (services.affiliates.user_discount):
    a coupon on a first subscription, a lower price on page packs. Stripe allows
    either a discount or promotion codes on a session, so a discounted checkout
    doesn't show the promo-code box.
    """
    if not _stripe_available():
        logger.warning("Stripe not configured; cannot create checkout session")
        return None
    stripe.api_key = _STRIPE_KEY
    success_url = success_url or f"{_FRONTEND_URL}/settings?checkout=success"
    cancel_url = cancel_url or f"{_FRONTEND_URL}/settings?checkout=cancelled"
    customer_id = get_or_create_stripe_customer(user_id, email)
    if not customer_id:
        return None
    ga_meta = {k: str(v)[:64] for k, v in (("ga_client_id", ga_client_id), ("ga_session_id", ga_session_id)) if v}
    if ad_opt_out:
        ga_meta["ad_opt_out"] = "1"  # read back by the webhook; see _ad_opt_out
    discount = _referral_discount(user_id)
    try:
        if mode == "subscription":
            subscription_data: dict = {"metadata": {"user_id": user_id, **ga_meta}}
            trial_days = offer_trial_days(offer)
            if trial_days and not _has_had_subscription(customer_id):
                subscription_data["trial_period_days"] = trial_days
                subscription_data["metadata"]["offer"] = offer.strip().lower()
            promo: dict = {"allow_promotion_codes": True}
            coupon_id = None
            if discount and not _has_had_subscription(customer_id):  # first subscription only
                coupon_id = _referral_coupon_id(discount)
            if coupon_id:
                promo = {"discounts": [{"coupon": coupon_id}]}
                subscription_data["metadata"]["referral_code"] = discount["code"]
            session = stripe.checkout.Session.create(
                customer=customer_id,
                mode="subscription",
                line_items=[{"price": _PRICE_ID_MONTHLY, "quantity": 1}],
                success_url=success_url,
                cancel_url=cancel_url,
                client_reference_id=user_id,
                subscription_data=subscription_data,
                metadata={"user_id": user_id, **ga_meta},
                **promo,
            )
        else:
            pack_id = resolve_pack(pack, _is_subscribed(user_id))
            pages, price_cents = PAGE_PACKS[pack_id]
            promo = {"allow_promotion_codes": True}
            discount_meta: dict = {}
            if discount and discount["packs"]:
                price_cents = discounted_cents(price_cents, discount["pct"])
                promo = {}
                discount_meta = {"referral_code": discount["code"], "referral_discount_pct": str(discount["pct"])}
            session = stripe.checkout.Session.create(
                customer=customer_id,
                mode="payment",
                line_items=[{
                    "price_data": {
                        "currency": "usd",
                        "unit_amount": price_cents,
                        "product_data": {"name": f"{pages} extra pages", "description": (
                            "Bank Statement Scanner subscriber page pack. Never expires; paused if you cancel your plan."
                            if pack_id in SUBSCRIBER_PACKS else "Bank Statement Scanner page pack. Never expires."
                        )},
                    },
                    "quantity": 1,
                }],
                success_url=success_url,
                cancel_url=cancel_url,
                client_reference_id=user_id,
                metadata={"user_id": user_id, "topup": "1", "pack": pack_id, "pack_pages": str(pages), **discount_meta, **ga_meta},
                **promo,
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

    # Support both the canonical invoice event type and the variant emitted by some Stripe tools
    if event.type in ("invoice.payment_succeeded", "invoice_payment.paid"):
        return _handle_invoice_paid(event)
    if event.type in ("customer.subscription.created", "customer.subscription.updated"):
        return _handle_subscription_updated(event)
    if event.type == "customer.subscription.deleted":
        return _handle_subscription_deleted(event)
    if event.type == "checkout.session.completed":
        return _handle_checkout_completed(event)
    return True, "Event ignored"


def _handle_invoice_paid(event) -> tuple[bool, str]:
    invoice = event["data"]["object"]
    billing_reason = invoice.get("billing_reason")
    customer_id = invoice.get("customer")
    subscription_id = _invoice_subscription_id(invoice)
    if not customer_id:
        return True, "No customer"

    user_id = _user_id_from_customer(customer_id, subscription_id, invoice.get("client_reference_id"))
    sub_meta = _invoice_subscription_metadata(invoice)
    if not user_id and _is_paid_signup(sub_meta):
        user_id = _paid_signup_user(customer_id, sub_meta, invoice.get("customer_email"))
        if not user_id:
            return False, "Paid signup account not ready; retry"  # non-2xx -> Stripe retries
    if not user_id:
        return True, "Could not resolve user_id"

    amount_paid = invoice.get("amount_paid") or 0  # cents

    # Subscription cycle or create: reset the monthly allowance to PLAN_PAGES
    if billing_reason in ("subscription_cycle", "subscription_create") and subscription_id:
        try:
            set_plan_pages(user_id, PLAN_PAGES)
            set_stripe_ids(user_id, customer_id, subscription_id)
        except Exception as e:
            logger.exception("set_plan_pages failed: %s", e)
            return False, str(e)
        # First paid month only (not renewals): report the checkout to LinkedIn
        if billing_reason == "subscription_create" and not _ad_opt_out(_invoice_subscription_metadata(invoice)):
            try:
                track_subscription_purchase(
                    email=invoice.get("customer_email"),
                    event_id=invoice.get("id"),
                    amount_cents=amount_paid,
                    currency=invoice.get("currency"),
                )
            except Exception as e:  # noqa: BLE001
                logger.warning("LinkedIn purchase conversion failed (continuing): %s", e)
        if amount_paid > 0:
            record_affiliate_payment(
                user_id, invoice.get("id"), amount_paid - _invoice_tax_cents(invoice), invoice.get("currency"), "subscription"
            )
            _track_ga4(
                user_id,
                "purchase",
                {
                    "transaction_id": invoice.get("id"),
                    "value": amount_paid / 100,
                    "currency": (invoice.get("currency") or "usd").upper(),
                    "payment_type": "subscription_first" if billing_reason == "subscription_create" else "subscription_renewal",
                    "items": [{"item_id": "monthly", "item_name": "Monthly subscription", "price": amount_paid / 100, "quantity": 1}],
                },
                _invoice_subscription_metadata(invoice),
            )
        return True, f"Plan pages set to {PLAN_PAGES}"

    # Page packs are credited from checkout.session.completed only (never here,
    # so a pack paid via an invoice can't be credited twice).
    return True, "OK"


def _handle_subscription_updated(event) -> tuple[bool, str]:
    sub = event["data"]["object"]
    customer_id = sub.get("customer")
    user_id = _user_id_from_customer(customer_id, sub.get("id"), None)
    meta = sub.get("metadata") or {}
    if not user_id and _is_paid_signup(meta) and sub.get("status") in ("active", "trialing"):
        user_id = _paid_signup_user(customer_id, meta)
        if not user_id:
            return False, "Paid signup account not ready; retry"
    if user_id and sub.get("status") in ("active", "trialing"):
        set_stripe_ids(user_id, customer_id, sub.get("id"))
    return True, "OK"


def _handle_subscription_deleted(event) -> tuple[bool, str]:
    sub = event["data"]["object"]
    customer_id = sub.get("customer")
    user_id = _user_id_from_customer(customer_id, sub.get("id"), None)
    if user_id:
        # Plan allowance ends; subscriber packs stay but freeze until they subscribe again.
        clear_subscription(user_id, sub.get("id"))
    return True, "OK"


# Promotion codes (or their coupons) with metadata bonus_pages=<n> add n free
# pack pages to the checkout that uses them, e.g. REDDIT200. Set up in Stripe;
# no deploy needed for new codes. Capped as a guard against a metadata typo.
_MAX_BONUS_PAGES = 1000


def _metadata_bonus(obj) -> int:
    try:
        return max(0, int(((obj or {}).get("metadata") or {}).get("bonus_pages") or 0))
    except (TypeError, ValueError):
        return 0


def _promo_bonus_pages(session) -> int:
    """Bonus pages from promotion codes applied to a Checkout Session. Raises on Stripe errors (webhook retries).

    Stripe can't limit a code to once per customer, so the first session to use
    a bonus code is recorded on the customer (metadata bonus_<promo id> =
    session id); later sessions by that customer get the discount but no bonus.
    A webhook retry of the recorded session still gets it.
    """
    bonus = 0
    for d in session.get("discounts") or []:
        promo, coupon = d.get("promotion_code"), d.get("coupon")
        if isinstance(promo, str):
            stripe.api_key = _STRIPE_KEY
            promo = stripe.PromotionCode.retrieve(promo)
        if isinstance(coupon, str):
            coupon = None  # the promo code carries its coupon
        coupon = coupon or (promo or {}).get("coupon")
        pages = _metadata_bonus(promo) or _metadata_bonus(coupon)
        if pages and _claim_bonus(session, (promo or {}).get("id") or (coupon or {}).get("id")):
            bonus += pages
    return min(bonus, _MAX_BONUS_PAGES)


def _claim_bonus(session, promo_id: str | None) -> bool:
    """True if this session may take `promo_id`'s bonus for its customer (first use, or a retry of it)."""
    customer_id = session.get("customer")
    if not customer_id or not promo_id:
        return False
    stripe.api_key = _STRIPE_KEY
    key = f"bonus_{promo_id}"[:40]
    customer = stripe.Customer.retrieve(customer_id)
    claimed = (customer.get("metadata") or {}).get(key)
    if claimed:
        return claimed == session.get("id")
    stripe.Customer.modify(customer_id, metadata={key: session.get("id")})
    return True


def _grant_promo_bonus(user_id: str, session) -> tuple[bool, int]:
    """Add any promo-code bonus pages. Returns (ok, pages); ok=False means retry the webhook."""
    try:
        bonus = _promo_bonus_pages(session)
        if bonus:
            add_pack_pages(user_id, bonus)
            logger.info("Promo bonus: user=%s pages=%d session=%s", user_id, bonus, session.get("id"))
        return True, bonus
    except Exception as e:  # noqa: BLE001
        logger.exception("Promo bonus failed on checkout.session.completed: %s", e)
        return False, 0


def _handle_checkout_completed(event) -> tuple[bool, str]:
    """Top-up payments (mode=payment) credit the balance; subscription checkouts report `subscribe` to GA4.
    Either kind also credits promo-code bonus pages (see _promo_bonus_pages)."""
    session = event["data"]["object"]
    metadata = session.get("metadata") or {}

    if session.get("mode") == "subscription":
        user_id = metadata.get("user_id") or session.get("client_reference_id")
        if not user_id and _is_paid_signup(metadata):
            details = session.get("customer_details") or {}
            user_id = _paid_signup_user(session.get("customer"), metadata, details.get("email"), details.get("name"))
            if not user_id:
                return False, "Paid signup account not ready; retry"
        if user_id:
            ok, _ = _grant_promo_bonus(user_id, session)
            if not ok:
                return False, "Promo bonus failed; retry"
            _track_ga4(
                user_id,
                "subscribe",
                {
                    "transaction_id": session.get("id"),
                    "value": (session.get("amount_total") or 0) / 100,
                    "currency": (session.get("currency") or "usd").upper(),
                    "trial": "yes" if not session.get("amount_total") else "no",
                },
                metadata,
            )
        return True, "Subscription checkout tracked"

    # Only care about payment mode sessions
    if session.get("mode") != "payment":
        return True, "Ignored checkout.session.completed (not payment mode)"

    is_topup = str(metadata.get("topup", "")).strip() == "1"
    if not is_topup:
        return True, "Ignored checkout.session.completed (not top-up)"

    # Prefer explicit user_id in metadata, then client_reference_id, then lookup by customer
    user_id = metadata.get("user_id") or session.get("client_reference_id")
    if not user_id:
        customer_id = session.get("customer")
        user_id = _user_id_from_customer(customer_id, None, None)
    if not user_id:
        return True, "Could not resolve user_id for checkout.session.completed"

    amount = session.get("amount_total") or 0  # cents (after any promo code)
    pages = _pack_pages_from_metadata(metadata, amount)
    if pages <= 0:
        return True, "No pages to apply for top-up"
    try:
        bonus = _promo_bonus_pages(session)
    except Exception as e:  # noqa: BLE001
        logger.exception("Promo bonus lookup failed on checkout.session.completed: %s", e)
        return False, str(e)  # before crediting anything, so the retry is clean

    try:
        # Subscriber packs freeze if the plan ends; bulk packs and promo bonuses never do.
        # One write: a retry can't double-credit just the bonus.
        if str(metadata.get("pack", "")).strip() in SUBSCRIBER_PACKS:
            add_pack_pages(user_id, bonus, sub_pages=pages)
        else:
            add_pack_pages(user_id, pages + bonus)
    except Exception as e:
        logger.exception("add_pack_pages failed on checkout.session.completed: %s", e)
        return False, str(e)
    tax = int(((session.get("total_details") or {}).get("amount_tax")) or 0)
    record_affiliate_payment(user_id, session.get("id"), amount - tax, session.get("currency"), "pack")
    _track_ga4(
        user_id,
        "purchase",
        {
            "transaction_id": session.get("id"),
            "value": amount / 100,
            "currency": (session.get("currency") or "usd").upper(),
            "payment_type": "topup",
            "items": [{"item_id": f"pages_{pages}", "item_name": f"{pages} page pack", "price": amount / 100, "quantity": 1}],
        },
        metadata,
    )
    return True, f"Top-up applied: {pages} pages" + (f" + {bonus} promo bonus" if bonus else "")


def _pack_pages_from_metadata(metadata: dict, amount_cents: int) -> int:
    """Pages bought in a top-up checkout. Server-set pack id wins; legacy $-credit sessions convert by amount."""
    pack_id = str(metadata.get("pack", "")).strip()
    if pack_id in PAGE_PACKS:
        return PAGE_PACKS[pack_id][0]
    return max(0, int(amount_cents or 0)) // _LEGACY_CENTS_PER_PAGE


def _invoice_subscription_id(invoice) -> str | None:
    """Subscription id on an invoice (older and newer Stripe API shapes).

    From API 2025-03-31.basil on, `invoice.subscription` is gone and the id lives
    at `invoice.parent.subscription_details.subscription`. Reading only the old
    field made subscription invoices look like top-ups and ignored $0 invoices.
    """
    sub = invoice.get("subscription")
    if not sub:
        details = (invoice.get("parent") or {}).get("subscription_details") or {}
        sub = details.get("subscription")
    if isinstance(sub, dict):  # expanded object
        sub = sub.get("id")
    return sub or None


def _invoice_tax_cents(invoice) -> int:
    """Tax on an invoice (older `tax` field or newer `total_taxes` list). Commissions are on pre-tax revenue."""
    if invoice.get("tax") is not None:
        return int(invoice.get("tax") or 0)
    return sum(int((t or {}).get("amount") or 0) for t in (invoice.get("total_taxes") or []))


def _invoice_subscription_metadata(invoice) -> dict:
    """Subscription metadata copied onto the invoice (older and newer Stripe API shapes)."""
    details = invoice.get("subscription_details") or (invoice.get("parent") or {}).get("subscription_details") or {}
    return details.get("metadata") or {}


def _ad_opt_out(metadata: dict | None) -> bool:
    """The buyer's browser sent Global Privacy Control at checkout (opt-out of sale/sharing)."""
    return str((metadata or {}).get("ad_opt_out", "")) == "1"


def _track_ga4(user_id: str, event_name: str, params: dict, metadata: dict | None) -> None:
    try:
        client_id, session_id = ga_ids_from_metadata(metadata)
        track_event(user_id, event_name, params, client_id, session_id, ad_opt_out=_ad_opt_out(metadata))
    except Exception as e:  # noqa: BLE001 - analytics must never fail a webhook
        logger.warning("GA4 %s event failed (continuing): %s", event_name, e)


def _is_paid_signup(metadata: dict | None) -> bool:
    """Checkout started from the pricing page with no account (services.paid_signup)."""
    return (metadata or {}).get("flow") == "paid_signup"


def _paid_signup_user(customer_id: str | None, metadata: dict, email: str | None = None, name: str | None = None) -> str | None:
    """Create/link the account for a paid signup; its user_id, or None if not possible yet."""
    from services import paid_signup  # imports billing; avoid a cycle at import time

    try:
        acct = paid_signup.ensure_account(customer_id, email, metadata.get("referral_code"), name)
    except Exception as e:  # noqa: BLE001
        logger.exception("paid signup ensure_account failed: %s", e)
        return None
    return acct["user_id"] if acct else None


def _user_id_from_customer(stripe_customer_id: str | None, subscription_id: str | None, client_reference_id: str | None) -> str | None:
    """Resolve user_id from client_reference_id or stripe_customer_id lookup."""
    if client_reference_id:
        return client_reference_id
    if stripe_customer_id:
        return get_user_id_by_stripe_customer_id(stripe_customer_id)
    return None
