"""Tests for ad-campaign offers applied at subscription checkout."""
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from stripe import StripeError

from services import billing


@pytest.fixture
def stripe_configured(monkeypatch):
    monkeypatch.setattr(billing, "_STRIPE_KEY", "sk_test")
    monkeypatch.setattr(billing, "_PRICE_ID_MONTHLY", "price_m")
    monkeypatch.setattr(billing, "_PRICE_ID_TOPUP", "price_t")
    monkeypatch.setattr(billing, "get_or_create_stripe_customer", lambda uid, email: "cus_1")


def _checkout(offer, prior_subs=()):
    with patch.object(billing.stripe.Subscription, "list", return_value=SimpleNamespace(data=list(prior_subs))), \
         patch.object(billing.stripe.checkout.Session, "create",
                      return_value=SimpleNamespace(url="https://stripe/x", id="cs_1")) as create:
        result = billing.create_checkout_session("user-1", "subscription", offer=offer)
    assert result == {"url": "https://stripe/x", "sessionId": "cs_1"}
    return create.call_args.kwargs["subscription_data"]


def test_offer_trial_days():
    assert billing.offer_trial_days("linkedin1m") == 30
    assert billing.offer_trial_days(" LinkedIn1M ") == 30
    assert billing.offer_trial_days("made-up") == 0
    assert billing.offer_trial_days(None) == 0


def test_known_offer_adds_trial_for_first_time_subscriber(stripe_configured):
    data = _checkout("linkedin1m")
    assert data["trial_period_days"] == 30
    assert data["metadata"] == {"user_id": "user-1", "offer": "linkedin1m"}


def test_unknown_offer_ignored(stripe_configured):
    data = _checkout("free-forever")
    assert "trial_period_days" not in data


def test_offer_ignored_for_returning_subscriber(stripe_configured):
    data = _checkout("linkedin1m", prior_subs=[object()])
    assert "trial_period_days" not in data


def test_offer_fails_closed_on_stripe_error(stripe_configured):
    with patch.object(billing.stripe.Subscription, "list", side_effect=StripeError("down")):
        assert billing._has_had_subscription("cus_1") is True
