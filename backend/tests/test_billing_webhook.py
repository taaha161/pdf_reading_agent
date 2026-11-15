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
def test_topup_checkout_credits_pack_pages(pack, pages):
    session = {"id": "cs_1", "mode": "payment", "amount_total": billing.PAGE_PACKS[pack][1], "currency": "usd",
               "metadata": {"user_id": "user-1", "topup": "1", "pack": pack}}
    with patch.object(billing, "add_pack_pages") as add_pack, patch.object(billing, "_track_ga4"):
        ok, _ = billing._handle_checkout_completed({"data": {"object": session}})
    assert ok
    add_pack.assert_called_once_with("user-1", pages)


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


def test_subscription_deleted_clears_plan_pages_only():
    event = {"data": {"object": {"id": "sub_1", "customer": "cus_1"}}}
    with patch.object(billing, "_user_id_from_customer", return_value="user-1"), \
         patch.object(billing, "set_stripe_ids"), patch.object(billing, "set_plan_pages") as set_plan, \
         patch.object(billing, "add_pack_pages") as add_pack:
        billing._handle_subscription_deleted(event)
    set_plan.assert_called_once_with("user-1", 0)
    add_pack.assert_not_called()


@pytest.mark.parametrize("pages,mode,cost", [(1, "fast", 1), (12, "balanced", 12), (12, "accurate", 24), (0, "fast", 1)])
def test_scan_cost_pages(pages, mode, cost):
    assert billing.scan_cost_pages(pages, mode) == cost
