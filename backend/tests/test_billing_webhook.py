"""Subscription invoice webhooks across Stripe API payload shapes.

From API 2025-03-31.basil (and the account's 2026-02-25.clover), invoices carry
the subscription at parent.subscription_details.subscription, not invoice.subscription.
"""
from unittest.mock import patch

import pytest

from services import billing


def _invoice(billing_reason, amount_paid, shape):
    invoice = {
        "id": "in_1",
        "billing_reason": billing_reason,
        "customer": "cus_1",
        "customer_email": "jane@example.com",
        "amount_paid": amount_paid,
        "currency": "usd",
    }
    if shape == "legacy":
        invoice["subscription"] = "sub_1"
    else:
        invoice["parent"] = {
            "type": "subscription_details",
            "subscription_details": {"subscription": "sub_1", "metadata": {"user_id": "user-1"}},
        }
    return {"data": {"object": invoice}}


def _handle(event):
    with patch.object(billing, "_user_id_from_customer", return_value="user-1"), \
         patch.object(billing, "set_plan_pages") as set_plan, \
         patch.object(billing, "add_pack_pages") as add_pack, \
         patch.object(billing, "set_stripe_ids") as set_ids, \
         patch.object(billing, "track_subscription_purchase"), \
         patch.object(billing, "_track_ga4"):
        ok, _ = billing._handle_invoice_paid(event)
    assert ok
    return set_plan, add_pack, set_ids


@pytest.mark.parametrize("shape", ["legacy", "parent"])
@pytest.mark.parametrize("reason", ["subscription_create", "subscription_cycle"])
def test_paid_subscription_invoice_resets_plan_pages(shape, reason):
    set_plan, add_pack, set_ids = _handle(_invoice(reason, 1000, shape))
    set_plan.assert_called_once_with("user-1", billing.PLAN_PAGES)
    add_pack.assert_not_called()  # must not be treated as a top-up
    set_ids.assert_called_once_with("user-1", "cus_1", "sub_1")


@pytest.mark.parametrize("shape", ["legacy", "parent"])
def test_free_first_invoice_still_grants_plan_pages(shape):
    """100%-off coupon or trial: $0 invoice must still activate the subscription."""
    set_plan, add_pack, set_ids = _handle(_invoice("subscription_create", 0, shape))
    set_plan.assert_called_once_with("user-1", billing.PLAN_PAGES)
    add_pack.assert_not_called()
    set_ids.assert_called_once_with("user-1", "cus_1", "sub_1")


def test_subscription_id_helper_shapes():
    assert billing._invoice_subscription_id({"subscription": "sub_a"}) == "sub_a"
    assert billing._invoice_subscription_id({"subscription": {"id": "sub_b"}}) == "sub_b"
    assert billing._invoice_subscription_id(
        {"parent": {"subscription_details": {"subscription": "sub_c"}}}
    ) == "sub_c"
    assert billing._invoice_subscription_id({"parent": None}) is None
    assert billing._invoice_subscription_id({}) is None


@pytest.mark.parametrize("pack,pages", [("10", 10), ("30", 30), ("100", 100)])
def test_subscriber_pack_credits_freezable_bucket(pack, pages):
    session = {"id": "cs_1", "mode": "payment", "amount_total": billing.PAGE_PACKS[pack][1], "currency": "usd",
               "metadata": {"user_id": "user-1", "topup": "1", "pack": pack}}
    with patch.object(billing, "add_pack_pages") as add_pack, patch.object(billing, "_track_ga4"):
        ok, _ = billing._handle_checkout_completed({"data": {"object": session}})
    assert ok
    add_pack.assert_called_once_with("user-1", 0, sub_pages=pages)


def test_bulk_pack_credits_never_frozen_bucket():
    session = {"id": "cs_1", "mode": "payment", "amount_total": 4999, "currency": "usd",
               "metadata": {"user_id": "user-1", "topup": "1", "pack": "450"}}
    with patch.object(billing, "add_pack_pages") as add_pack, patch.object(billing, "_track_ga4"):
        ok, _ = billing._handle_checkout_completed({"data": {"object": session}})
    assert ok
    add_pack.assert_called_once_with("user-1", 450)


def test_legacy_topup_checkout_converts_cents_to_pages():
    session = {"id": "cs_1", "mode": "payment", "amount_total": 1000, "currency": "usd",
               "metadata": {"user_id": "user-1", "topup": "1"}}
    with patch.object(billing, "add_pack_pages") as add_pack, patch.object(billing, "_track_ga4"):
        billing._handle_checkout_completed({"data": {"object": session}})
    add_pack.assert_called_once_with("user-1", 100)


def test_non_subscription_invoice_never_credits_pages():
    invoice = {"id": "in_2", "billing_reason": "manual", "customer": "cus_1", "amount_paid": 500, "currency": "usd"}
    with patch.object(billing, "_user_id_from_customer", return_value="user-1"), \
         patch.object(billing, "add_pack_pages") as add_pack, patch.object(billing, "set_plan_pages") as set_plan:
        ok, _ = billing._handle_invoice_paid({"data": {"object": invoice}})
    assert ok
    add_pack.assert_not_called()
    set_plan.assert_not_called()


def test_subscription_deleted_clears_subscription_and_plan_pages():
    event = {"data": {"object": {"id": "sub_1", "customer": "cus_1"}}}
    with patch.object(billing, "_user_id_from_customer", return_value="user-1"), \
         patch.object(billing, "clear_subscription") as clear, \
         patch.object(billing, "add_pack_pages") as add_pack:
        billing._handle_subscription_deleted(event)
    clear.assert_called_once_with("user-1", "sub_1")
    add_pack.assert_not_called()


@pytest.mark.parametrize("pages,mode,cost", [(1, "fast", 1), (12, "balanced", 12), (12, "accurate", 24), (0, "fast", 1)])
def test_scan_cost_pages(pages, mode, cost):
    assert billing.scan_cost_pages(pages, mode) == cost


# --- promo-code bonus pages (e.g. REDDIT200: promotion code metadata bonus_pages=200) ---

def _pack_session(discounts, pack="450"):
    return {"id": "cs_1", "mode": "payment", "amount_total": 0, "currency": "usd", "customer": "cus_1",
            "metadata": {"user_id": "user-1", "topup": "1", "pack": pack}, "discounts": discounts}


def _checkout(session, promo=None, customer_meta=None):
    customer = {"id": "cus_1", "metadata": customer_meta or {}}
    with patch.object(billing, "add_pack_pages") as add_pack, \
         patch.object(billing, "_track_ga4"), \
         patch.object(billing.stripe.Customer, "retrieve", return_value=customer), \
         patch.object(billing.stripe.Customer, "modify"), \
         patch.object(billing.stripe.PromotionCode, "retrieve", return_value=promo) as retrieve:
        result = billing._handle_checkout_completed({"data": {"object": session}})
    return result, add_pack, retrieve


def test_promo_code_bonus_added_to_pack_pages():
    promo = {"id": "promo_1", "metadata": {"bonus_pages": "200"}, "coupon": {"id": "c1", "metadata": {}}}
    (ok, msg), add_pack, retrieve = _checkout(_pack_session([{"coupon": "c1", "promotion_code": "promo_1"}]), promo)
    assert ok and "200 promo bonus" in msg
    retrieve.assert_called_once_with("promo_1")
    add_pack.assert_called_once_with("user-1", 650)


def test_coupon_metadata_bonus_when_promo_has_none():
    promo = {"id": "promo_1", "metadata": {}, "coupon": {"id": "c1", "metadata": {"bonus_pages": "50"}}}
    (ok, _), add_pack, _ = _checkout(_pack_session([{"coupon": "c1", "promotion_code": "promo_1"}]), promo)
    add_pack.assert_called_once_with("user-1", 500)


def test_ordinary_discount_gives_no_bonus():
    promo = {"id": "promo_2", "metadata": {}, "coupon": {"id": "c2", "metadata": {}}}
    (ok, _), add_pack, _ = _checkout(_pack_session([{"coupon": "c2", "promotion_code": "promo_2"}]), promo)
    add_pack.assert_called_once_with("user-1", 450)


def test_no_discounts_skips_stripe_lookup():
    (ok, _), add_pack, retrieve = _checkout(_pack_session(None))
    retrieve.assert_not_called()
    add_pack.assert_called_once_with("user-1", 450)


def test_bonus_is_capped_and_bad_metadata_ignored():
    assert billing._metadata_bonus({"metadata": {"bonus_pages": "lots"}}) == 0
    promo = {"id": "p", "metadata": {"bonus_pages": "999999"}, "coupon": None}
    (ok, _), add_pack, _ = _checkout(_pack_session([{"promotion_code": "p"}]), promo)
    add_pack.assert_called_once_with("user-1", 450 + billing._MAX_BONUS_PAGES)


def test_stripe_error_fails_webhook_before_crediting():
    with patch.object(billing, "add_pack_pages") as add_pack, \
         patch.object(billing.stripe.PromotionCode, "retrieve", side_effect=billing.StripeError("down")):
        ok, _ = billing._handle_checkout_completed({"data": {"object": _pack_session([{"promotion_code": "p"}])}})
    assert not ok
    add_pack.assert_not_called()


def test_promo_bonus_on_subscriber_pack_never_freezes():
    promo = {"id": "promo_1", "metadata": {"bonus_pages": "200"}, "coupon": None}
    (ok, _), add_pack, _ = _checkout(_pack_session([{"promotion_code": "promo_1"}], pack="10"), promo)
    assert ok
    add_pack.assert_called_once_with("user-1", 200, sub_pages=10)


def test_promo_bonus_on_subscription_checkout():
    session = {"id": "cs_2", "mode": "subscription", "amount_total": 800, "currency": "usd", "customer": "cus_1",
               "metadata": {"user_id": "user-1"}, "discounts": [{"promotion_code": "promo_1"}]}
    promo = {"id": "promo_1", "metadata": {"bonus_pages": "200"}, "coupon": None}
    (ok, _), add_pack, _ = _checkout(session, promo)
    assert ok
    add_pack.assert_called_once_with("user-1", 200)


def test_bonus_only_once_per_customer_but_retry_still_credits():
    promo = {"id": "promo_1", "metadata": {"bonus_pages": "200"}, "coupon": None}
    session = _pack_session([{"promotion_code": "promo_1"}])
    (_, _), add_pack, _ = _checkout(session, promo, customer_meta={"bonus_promo_1": "cs_other"})
    add_pack.assert_called_once_with("user-1", 450)  # second use: no bonus
    (_, _), add_pack, _ = _checkout(session, promo, customer_meta={"bonus_promo_1": "cs_1"})
    add_pack.assert_called_once_with("user-1", 650)  # webhook retry of the first use


def test_first_use_records_session_on_customer():
    promo = {"id": "promo_1", "metadata": {"bonus_pages": "200"}, "coupon": None}
    with patch.object(billing, "add_pack_pages"), patch.object(billing, "_track_ga4"), \
         patch.object(billing.stripe.PromotionCode, "retrieve", return_value=promo), \
         patch.object(billing.stripe.Customer, "retrieve", return_value={"id": "cus_1", "metadata": {}}), \
         patch.object(billing.stripe.Customer, "modify") as modify:
        billing._handle_checkout_completed({"data": {"object": _pack_session([{"promotion_code": "promo_1"}])}})
    modify.assert_called_once_with("cus_1", metadata={"bonus_promo_1": "cs_1"})
