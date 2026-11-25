"""Affiliate program: code claims, commission math, webhook wiring, admin API."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import patch

import pytest

from services import affiliates, billing

NOW = datetime(2026, 11, 15, tzinfo=timezone.utc)
AFF = {"id": "aff-1", "active": True}


# --- claim_referral ---

def _claim(code="Jane-10", affiliate=AFF, created_at=NOW - timedelta(hours=1), bound=True):
    with patch.object(affiliates, "get_affiliate_by_code", return_value=affiliate) as get_aff, \
         patch.object(affiliates, "get_user_created_at", return_value=created_at), \
         patch.object(affiliates, "create_referral", return_value=bound) as create:
        result = affiliates.claim_referral("user-1", code, now=NOW)
    return result, get_aff, create


def test_claim_binds_new_account_with_lowercased_code():
    (ok, reason), get_aff, create = _claim(code="  Jane-10 ")
    assert (ok, reason) == (True, "ok")
    get_aff.assert_called_once_with("jane-10")
    create.assert_called_once_with("user-1", "aff-1", "jane-10")


@pytest.mark.parametrize("code", ["", "ab", "has space", "x" * 33, "bad$char"])
def test_claim_rejects_malformed_code_without_db(code):
    (ok, reason), get_aff, _ = _claim(code=code)
    assert (ok, reason) == (False, "invalid_code")
    get_aff.assert_not_called()


def test_claim_rejects_unknown_and_inactive_codes():
    assert _claim(affiliate=None)[0] == (False, "unknown_code")
    assert _claim(affiliate={**AFF, "active": False})[0] == (False, "unknown_code")


def test_claim_rejects_old_accounts():
    (ok, reason), _, create = _claim(created_at=NOW - affiliates.CLAIM_WINDOW - timedelta(minutes=1))
    assert (ok, reason) == (False, "account_too_old")
    create.assert_not_called()


def test_claim_first_binding_wins():
    assert _claim(bound=False)[0] == (False, "already_referred")


# --- commission math ---

@pytest.mark.parametrize("amount,pct,expected", [
    (1000, 20, 200),
    (1000, Decimal("12.5"), 125),
    (500, Decimal("33.33"), 167),  # 166.65 rounds half-up
    (200, 0, 0),
    (1000, 100, 1000),
])
def test_commission_cents(amount, pct, expected):
    assert affiliates.commission_cents(amount, pct) == expected


# --- record_payment ---

def _ref(**kw):
    return {"affiliate_id": "aff-1", "revenue_share_pct": Decimal("20"), "commission_months": None,
            "active": True, "referred_at": NOW - timedelta(days=10), **kw}


def _record(ref, amount=1000, now=NOW, inserted=True):
    with patch.object(affiliates, "get_referral_with_affiliate", return_value=ref), \
         patch.object(affiliates, "insert_commission", return_value=inserted) as insert:
        result = affiliates.record_payment("user-1", "in_1", amount, "USD", "subscription", now=now)
    return result, insert


def test_record_payment_for_referred_user():
    cents, insert = _record(_ref())
    assert cents == 200
    insert.assert_called_once_with(
        affiliate_id="aff-1", user_id="user-1", source_id="in_1", kind="subscription",
        amount_cents=1000, currency="usd", revenue_share_pct=Decimal("20"), commission_cents=200,
    )


def test_record_payment_skips_unreferred_inactive_and_zero():
    assert _record(None)[1].call_count == 0
    assert _record(_ref(active=False))[1].call_count == 0
    assert _record(_ref(), amount=0)[1].call_count == 0


def test_record_payment_respects_commission_window():
    ref = _ref(commission_months=12, referred_at=NOW - timedelta(days=30 * 12 + 1))
    assert _record(ref)[1].call_count == 0
    ref = _ref(commission_months=12, referred_at=NOW - timedelta(days=30 * 12 - 1))
    assert _record(ref)[0] == 200


def test_record_payment_duplicate_webhook_returns_none():
    assert _record(_ref(), inserted=False)[0] is None


def test_record_payment_never_raises():
    with patch.object(affiliates, "get_referral_with_affiliate", side_effect=RuntimeError("db down")):
        assert affiliates.record_payment("user-1", "in_1", 1000, "usd", "pack") is None


# --- webhook wiring ---

def test_subscription_invoice_records_pre_tax_commission(affiliate_payment):
    invoice = {"id": "in_9", "billing_reason": "subscription_cycle", "customer": "cus_1",
               "subscription": "sub_1", "amount_paid": 1080, "tax": 80, "currency": "usd"}
    with patch.object(billing, "_user_id_from_customer", return_value="user-1"), \
         patch.object(billing, "set_plan_pages"), patch.object(billing, "set_stripe_ids"), \
         patch.object(billing, "_track_ga4"):
        ok, _ = billing._handle_invoice_paid({"data": {"object": invoice}})
    assert ok
    affiliate_payment.assert_called_once_with("user-1", "in_9", 1000, "usd", "subscription")


def test_trial_invoice_records_no_commission(affiliate_payment):
    invoice = {"id": "in_0", "billing_reason": "subscription_create", "customer": "cus_1",
               "subscription": "sub_1", "amount_paid": 0, "currency": "usd"}
    with patch.object(billing, "_user_id_from_customer", return_value="user-1"), \
         patch.object(billing, "set_plan_pages"), patch.object(billing, "set_stripe_ids"), \
         patch.object(billing, "track_subscription_purchase"), patch.object(billing, "_track_ga4"):
        billing._handle_invoice_paid({"data": {"object": invoice}})
    affiliate_payment.assert_not_called()


def test_page_pack_checkout_records_commission(affiliate_payment):
    session = {"id": "cs_1", "mode": "payment", "amount_total": 500, "currency": "usd",
               "total_details": {"amount_tax": 0},
               "metadata": {"user_id": "user-1", "topup": "1", "pack": "30"}}
    with patch.object(billing, "add_pack_pages"), patch.object(billing, "_track_ga4"):
        ok, _ = billing._handle_checkout_completed({"data": {"object": session}})
    assert ok
    affiliate_payment.assert_called_once_with("user-1", "cs_1", 500, "usd", "pack")


def test_invoice_tax_newer_api_shape():
    assert billing._invoice_tax_cents({"total_taxes": [{"amount": 50}, {"amount": 30}]}) == 80
    assert billing._invoice_tax_cents({}) == 0


# --- endpoints ---

ADMIN = {"Authorization": "Bearer test-admin-secret"}


@pytest.fixture
def admin(monkeypatch):
    import main
    monkeypatch.setattr(main, "_ADMIN_SECRET", "test-admin-secret")


def test_admin_endpoints_require_secret(client, admin):
    assert client.get("/admin/affiliates").status_code == 401
    assert client.get("/admin/affiliates", headers={"Authorization": "Bearer wrong"}).status_code == 401


def test_admin_create_affiliate(client, admin):
    row = {"id": "aff-1", "code": "jane"}
    with patch("store.create_affiliate", return_value=row) as create:
        r = client.post("/admin/affiliates", headers=ADMIN,
                        json={"name": " Jane ", "code": "JANE", "revenue_share_pct": 25})
    assert r.status_code == 201
    create.assert_called_once_with(name="Jane", code="jane", revenue_share_pct=25,
                                   email=None, commission_months=None, notes=None,
                                   discount_pct=0, discount_months=None, discount_packs=False)


def test_admin_create_rejects_bad_code_and_pct(client, admin):
    assert client.post("/admin/affiliates", headers=ADMIN,
                       json={"name": "J", "code": "a b", "revenue_share_pct": 25}).status_code == 400
    assert client.post("/admin/affiliates", headers=ADMIN,
                       json={"name": "J", "code": "jane", "revenue_share_pct": 150}).status_code == 422


def test_admin_create_duplicate_code(client, admin):
    import psycopg2.errors
    with patch("store.create_affiliate", side_effect=psycopg2.errors.UniqueViolation()):
        r = client.post("/admin/affiliates", headers=ADMIN,
                        json={"name": "J", "code": "jane", "revenue_share_pct": 25})
    assert r.status_code == 409


def test_admin_update_only_sends_set_fields(client, admin):
    with patch("store.update_affiliate", return_value={"id": "x"}) as update:
        r = client.patch("/admin/affiliates/00000000-0000-0000-0000-000000000001", headers=ADMIN,
                         json={"revenue_share_pct": 30})
    assert r.status_code == 200
    update.assert_called_once_with("00000000-0000-0000-0000-000000000001", {"revenue_share_pct": 30})


def test_referral_claim_endpoint(client):
    with patch("main.claim_referral", return_value=(True, "ok")) as claim:
        r = client.post("/api/referral/claim", json={"code": "jane"})
    assert r.json() == {"ok": True, "reason": "ok"}
    claim.assert_called_once_with("test-user-id", "jane")


# --- user discount ---

def _disc_ref(**kw):
    terms = {"discount_pct": Decimal("20"), "discount_months": 3, "discount_packs": True,
             "stripe_coupon_id": None, "code": "jane"}
    return _ref(**{**terms, **kw})


def _discount(ref, now=NOW):
    with patch.object(affiliates, "get_referral_with_affiliate", return_value=ref):
        return affiliates.user_discount("user-1", now=now)


def test_user_discount_terms():
    d = _discount(_disc_ref())
    assert d["pct"] == 20 and d["months"] == 3 and d["packs"] is True and d["code"] == "jane"
    assert d["packs_ends_at"] == NOW - timedelta(days=10) + timedelta(days=90)


def test_user_discount_none_without_pct_or_referral_or_when_inactive():
    assert _discount(None) is None
    assert _discount(_ref(discount_pct=0)) is None
    assert _discount(_disc_ref(active=False)) is None


def test_pack_discount_expires_but_plan_discount_stays():
    d = _discount(_disc_ref(), now=NOW + timedelta(days=100))
    assert d is not None and d["packs"] is False and d["packs_ends_at"] is None


def test_forever_discount_never_expires():
    d = _discount(_disc_ref(discount_months=None), now=NOW + timedelta(days=3650))
    assert d["packs"] is True and d["packs_ends_at"] is None


def test_public_discount_hides_affiliate():
    aff = {**AFF, "name": "Jane", "discount_pct": Decimal("15"), "discount_months": None, "discount_packs": False}
    with patch.object(affiliates, "get_affiliate_by_code", return_value=aff):
        assert affiliates.public_discount("JANE") == {"valid": True, "discount": {"pct": 15.0, "months": None, "packs": False}}
    with patch.object(affiliates, "get_affiliate_by_code", return_value={**AFF, "active": False}):
        assert affiliates.public_discount("jane") is None


@pytest.mark.parametrize("amount,pct,expected", [(500, 20, 400), (200, 90, 50), (1000, 100, 50)])
def test_discounted_cents_respects_stripe_minimum(amount, pct, expected):
    assert affiliates.discounted_cents(amount, pct) == expected


# --- checkout with discount ---

DISC = {"affiliate_id": "aff-1", "code": "jane", "pct": 20.0, "months": 3, "packs": True,
        "packs_ends_at": None, "stripe_coupon_id": None}


@pytest.fixture
def stripe_env(monkeypatch):
    monkeypatch.setattr(billing, "_STRIPE_KEY", "sk_test")
    monkeypatch.setattr(billing, "_PRICE_ID_MONTHLY", "price_1")
    monkeypatch.setattr(billing, "get_or_create_stripe_customer", lambda *a: "cus_1")


class _Session:
    url, id = "https://checkout", "cs_1"


def _checkout(mode, discount, had_sub=False, pack=None):
    from types import SimpleNamespace
    with patch.object(billing, "_referral_discount", return_value=discount), \
         patch.object(billing, "_has_had_subscription", return_value=had_sub), \
         patch.object(billing, "_is_subscribed", return_value=True), \
         patch.object(billing.stripe.Coupon, "create", return_value=SimpleNamespace(id="co_1")) as coupon, \
         patch.object(billing, "set_affiliate_coupon") as save_coupon, \
         patch.object(billing.stripe.checkout.Session, "create", return_value=_Session()) as create:
        billing.create_checkout_session("user-1", mode, pack=pack)
    return create.call_args.kwargs, coupon, save_coupon


def test_subscription_checkout_applies_referral_coupon(stripe_env):
    kwargs, coupon, save = _checkout("subscription", DISC)
    assert kwargs["discounts"] == [{"coupon": "co_1"}]
    assert "allow_promotion_codes" not in kwargs  # Stripe rejects both together
    coupon.assert_called_once_with(percent_off=20.0, name="Referral discount (JANE)",
                                   metadata={"affiliate_id": "aff-1", "code": "jane"},
                                   duration="repeating", duration_in_months=3)
    save.assert_called_once_with("aff-1", "co_1")


def test_subscription_checkout_reuses_cached_coupon_and_forever(stripe_env):
    kwargs, coupon, _ = _checkout("subscription", {**DISC, "stripe_coupon_id": "co_old"})
    assert kwargs["discounts"] == [{"coupon": "co_old"}]
    coupon.assert_not_called()


def test_forever_coupon_duration(stripe_env):
    _, coupon, _ = _checkout("subscription", {**DISC, "months": None})
    assert coupon.call_args.kwargs["duration"] == "forever"
    assert "duration_in_months" not in coupon.call_args.kwargs


def test_returning_subscriber_gets_no_referral_coupon(stripe_env):
    kwargs, coupon, _ = _checkout("subscription", DISC, had_sub=True)
    assert "discounts" not in kwargs and kwargs["allow_promotion_codes"] is True
    coupon.assert_not_called()


def test_no_discount_checkout_unchanged(stripe_env):
    kwargs, _, _ = _checkout("subscription", None)
    assert kwargs["allow_promotion_codes"] is True and "discounts" not in kwargs


def test_pack_checkout_discounted_price(stripe_env):
    kwargs, _, _ = _checkout("topup", DISC, pack="30")
    assert kwargs["line_items"][0]["price_data"]["unit_amount"] == 400  # $5 - 20%
    assert kwargs["metadata"]["pack"] == "30" and kwargs["metadata"]["referral_code"] == "jane"
    assert "allow_promotion_codes" not in kwargs


def test_pack_checkout_full_price_when_packs_not_discounted(stripe_env):
    kwargs, _, _ = _checkout("topup", {**DISC, "packs": False}, pack="30")
    assert kwargs["line_items"][0]["price_data"]["unit_amount"] == 500
    assert kwargs["allow_promotion_codes"] is True


def test_referral_lookup_endpoint(client):
    with patch("main.public_discount", return_value={"valid": True, "discount": None}):
        assert client.get("/api/referral/jane").json() == {"valid": True, "discount": None}
    with patch("main.public_discount", return_value=None):
        assert client.get("/api/referral/nope").status_code == 404


def test_balance_includes_referral_discount(client):
    d = {**DISC, "packs_ends_at": None}
    with patch("main._load_billing", return_value={"stripe_subscription_id": None}), \
         patch("main.user_discount", return_value=d):
        body = client.get("/api/billing/balance").json()
    assert body["referral_discount"]["pct"] == 20 and body["referral_discount"]["plan_eligible"] is True
