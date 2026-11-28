"""Tests for cancelling / resuming a subscription from the Account page."""
from unittest.mock import patch

import pytest
import stripe

from services import billing


@pytest.fixture
def subscribed(monkeypatch):
    monkeypatch.setattr(billing, "_STRIPE_KEY", "sk_test")
    monkeypatch.setattr(billing, "get_billing", lambda uid: {"stripe_subscription_id": "sub_1"})


def test_cancel_sets_period_end(subscribed):
    sub = {"status": "active", "cancel_at_period_end": True, "cancel_at": 1_800_000_000, "current_period_end": 1_800_000_000}
    with patch.object(stripe.Subscription, "modify", return_value=sub) as modify:
        out = billing.set_subscription_canceling("u1", True)
    modify.assert_called_once_with("sub_1", cancel_at_period_end=True)
    assert out == {"status": "active", "cancel_at_period_end": True, "current_period_end": 1_800_000_000}


def test_resume_clears_cancel(subscribed):
    sub = {"status": "active", "cancel_at_period_end": False, "cancel_at": None, "current_period_end": 1_800_000_000}
    pending = {**sub, "cancel_at_period_end": True, "cancel_at": 1_800_000_000}
    with patch.object(stripe.Subscription, "retrieve", return_value=pending), \
         patch.object(stripe.Subscription, "modify", return_value=sub) as modify:
        out = billing.set_subscription_canceling("u1", False)
    modify.assert_called_once_with("sub_1", cancel_at_period_end=False)
    assert out["cancel_at_period_end"] is False


def test_resume_clears_dashboard_end_date(subscribed):
    pending = {"status": "active", "cancel_at_period_end": False, "cancel_at": 1_800_000_000}
    with patch.object(stripe.Subscription, "retrieve", return_value=pending), \
         patch.object(stripe.Subscription, "modify", return_value={**pending, "cancel_at": None}) as modify:
        billing.set_subscription_canceling("u1", False)
    modify.assert_called_once_with("sub_1", cancel_at="")


def test_status_reads_period_from_item_on_new_api():
    sub = {"status": "active", "cancel_at_period_end": False, "items": {"data": [{"current_period_end": 42}]}}
    assert billing._subscription_view(sub)["current_period_end"] == 42


def test_no_subscription_raises(monkeypatch):
    monkeypatch.setattr(billing, "_STRIPE_KEY", "sk_test")
    monkeypatch.setattr(billing, "get_billing", lambda uid: {"stripe_subscription_id": None})
    with pytest.raises(billing.NoSubscription):
        billing.set_subscription_canceling("u1", True)
