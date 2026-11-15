"""Affiliate program: referral codes, signup binding, revenue-share commissions.

Affiliates are created by us (admin API) with their own code and revenue-share
percentage. A user who signs up with a code is bound to that affiliate once;
every payment that user makes afterwards (subscription invoices, page packs)
records a commission at the affiliate's percentage at that moment. Payouts are
manual: we pay the affiliate and mark their pending commissions paid.

An affiliate can also carry a discount for the users they refer: discount_pct
off the monthly plan for discount_months (NULL = forever) via a Stripe coupon,
and optionally the same percentage off page packs during that window.
Commissions are on what the user actually paid, so the discount reduces them.
"""
import logging
import re
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal

from store import (
    create_referral,
    get_affiliate_by_code,
    get_referral_with_affiliate,
    get_user_created_at,
    insert_commission,
)

logger = logging.getLogger("pdf_processor_app.affiliates")

CODE_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{2,31}$")
# A code can only be attached to an account this new, so existing users can't
# be retroactively claimed. Long enough for a late email confirmation.
CLAIM_WINDOW = timedelta(days=7)


def normalize_code(code: str | None) -> str:
    return (code or "").strip().lower()


def valid_code(code: str) -> bool:
    return bool(CODE_RE.match(code))


def claim_referral(user_id: str, code: str | None, now: datetime | None = None) -> tuple[bool, str]:
    """Bind a new account to the affiliate owning `code`. Returns (bound, reason)."""
    code = normalize_code(code)
    if not valid_code(code):
        return False, "invalid_code"
    affiliate = get_affiliate_by_code(code)
    if not affiliate or not affiliate["active"]:
        return False, "unknown_code"
    created_at = get_user_created_at(user_id)
    now = now or datetime.now(timezone.utc)
    if created_at is None or now - created_at > CLAIM_WINDOW:
        return False, "account_too_old"
    if not create_referral(user_id, str(affiliate["id"]), code):
        return False, "already_referred"
    logger.info("Referral bound: user=%s affiliate=%s", user_id, affiliate["id"])
    return True, "ok"


def _discount_terms(row: dict) -> dict | None:
    pct = Decimal(str(row.get("discount_pct") or 0))
    if pct <= 0:
        return None
    return {"pct": float(pct), "months": row.get("discount_months"), "packs": bool(row.get("discount_packs"))}


def public_discount(code: str | None) -> dict | None:
    """Discount a code gives at signup (for the signup form), or None if invalid/inactive.

    Returns {"valid": True, "discount": {...} | None}. Never exposes the affiliate.
    """
    code = normalize_code(code)
    if not valid_code(code):
        return None
    affiliate = get_affiliate_by_code(code)
    if not affiliate or not affiliate["active"]:
        return None
    return {"valid": True, "discount": _discount_terms(affiliate)}


def user_discount(user_id: str | None, now: datetime | None = None) -> dict | None:
    """The referral discount terms for this user, or None.

    {"affiliate_id", "code", "pct", "months", "packs", "packs_ends_at", "stripe_coupon_id"}.
    Subscription: `months` of discount counted from when they subscribe (the
    Stripe coupon's duration). Page packs: discounted only while `packs` is
    True, i.e. within `months` of signup (packs_ends_at; None = forever).
    """
    if not user_id:
        return None
    ref = get_referral_with_affiliate(user_id)
    if not ref or not ref["active"]:
        return None
    terms = _discount_terms(ref)
    if not terms:
        return None
    ends_at = _add_months(ref["referred_at"], terms["months"]) if terms["months"] else None
    if ends_at and (now or datetime.now(timezone.utc)) > ends_at:
        terms["packs"] = False
    return {
        **terms,
        "packs_ends_at": ends_at if terms["packs"] else None,
        "affiliate_id": str(ref["affiliate_id"]),
        "code": ref["code"],
        "stripe_coupon_id": ref.get("stripe_coupon_id"),
    }


# Stripe's minimum charge for a USD payment.
MIN_CHARGE_CENTS = 50


def discounted_cents(amount_cents: int, pct) -> int:
    """Price after `pct` percent off, never below Stripe's minimum charge."""
    return max(MIN_CHARGE_CENTS, int(amount_cents) - commission_cents(amount_cents, pct))


def commission_cents(amount_cents: int, pct) -> int:
    """`pct` percent of `amount_cents`, rounded half-up to the cent."""
    value = Decimal(int(amount_cents)) * Decimal(str(pct)) / Decimal(100)
    return int(value.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def _add_months(dt: datetime, months: int) -> datetime:
    # Calendar-ish months are fine for a commission window; 30-day months keep it simple.
    return dt + timedelta(days=30 * months)


def record_payment(
    user_id: str | None,
    source_id: str | None,
    amount_cents: int,
    currency: str | None,
    kind: str,
    now: datetime | None = None,
) -> int | None:
    """Record a commission if this paying user was referred. Returns commission cents or None.

    Never raises: commission bookkeeping must not fail a Stripe webhook.
    """
    if not user_id or not source_id or amount_cents <= 0:
        return None
    try:
        ref = get_referral_with_affiliate(user_id)
        if not ref or not ref["active"]:
            return None
        now = now or datetime.now(timezone.utc)
        months = ref.get("commission_months")
        if months and now > _add_months(ref["referred_at"], months):
            return None
        pct = ref["revenue_share_pct"]
        cents = commission_cents(amount_cents, pct)
        if cents <= 0:
            return None
        created = insert_commission(
            affiliate_id=str(ref["affiliate_id"]),
            user_id=user_id,
            source_id=source_id,
            kind=kind,
            amount_cents=int(amount_cents),
            currency=(currency or "usd").lower(),
            revenue_share_pct=pct,
            commission_cents=cents,
        )
        return cents if created else None
    except Exception as e:  # noqa: BLE001
        logger.exception("Affiliate commission failed (continuing): %s", e)
        return None
