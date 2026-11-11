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
         patch.object(billing, "set_balance") as set_balance, \
         patch.object(billing, "add_balance") as add_balance, \
         patch.object(billing, "set_stripe_ids") as set_ids, \
         patch.object(billing, "track_subscription_purchase"), \
         patch.object(billing, "_track_ga4"):
        ok, _ = billing._handle_invoice_paid(event)
    assert ok
    return set_balance, add_balance, set_ids


@pytest.mark.parametrize("shape", ["legacy", "parent"])
@pytest.mark.parametrize("reason", ["subscription_create", "subscription_cycle"])
def test_paid_subscription_invoice_resets_balance(shape, reason):
    set_balance, add_balance, set_ids = _handle(_invoice(reason, 1000, shape))
    set_balance.assert_called_once_with("user-1", 1000)
    add_balance.assert_not_called()  # must not be treated as a top-up
    set_ids.assert_called_once_with("user-1", "cus_1", "sub_1")


@pytest.mark.parametrize("shape", ["legacy", "parent"])
def test_free_first_invoice_still_grants_credits(shape):
    """100%-off coupon or trial: $0 invoice must still activate the subscription."""
    set_balance, add_balance, set_ids = _handle(_invoice("subscription_create", 0, shape))
    set_balance.assert_called_once_with("user-1", 1000)
    add_balance.assert_not_called()
    set_ids.assert_called_once_with("user-1", "cus_1", "sub_1")


def test_subscription_id_helper_shapes():
    assert billing._invoice_subscription_id({"subscription": "sub_a"}) == "sub_a"
    assert billing._invoice_subscription_id({"subscription": {"id": "sub_b"}}) == "sub_b"
    assert billing._invoice_subscription_id(
        {"parent": {"subscription_details": {"subscription": "sub_c"}}}
    ) == "sub_c"
    assert billing._invoice_subscription_id({"parent": None}) is None
    assert billing._invoice_subscription_id({}) is None
