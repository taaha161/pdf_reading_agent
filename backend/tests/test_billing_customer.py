"""Tests for stale Stripe customer ids in get_or_create_stripe_customer."""
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import stripe

from services import billing


@pytest.fixture
def setup(monkeypatch):
    monkeypatch.setattr(billing, "_STRIPE_KEY", "sk_test")
    monkeypatch.setattr(billing, "get_billing", lambda uid: {"stripe_customer_id": "cus_old"})
    saved = []
    monkeypatch.setattr(billing, "set_stripe_ids", lambda uid, cid, sid: saved.append(cid))
    return saved


def test_valid_stored_customer_is_reused(setup):
    with patch.object(stripe.Customer, "retrieve", return_value=SimpleNamespace(id="cus_old")), \
         patch.object(stripe.Customer, "create") as create:
        assert billing.get_or_create_stripe_customer("u1", "a@b.com") == "cus_old"
    create.assert_not_called()
    assert setup == []


def test_missing_customer_is_recreated(setup):
    err = stripe.InvalidRequestError("No such customer", "customer", code="resource_missing")
    with patch.object(stripe.Customer, "retrieve", side_effect=err), \
         patch.object(stripe.Customer, "create", return_value=SimpleNamespace(id="cus_new")):
        assert billing.get_or_create_stripe_customer("u1", "a@b.com") == "cus_new"
    assert setup == ["cus_new"]


def test_deleted_customer_is_recreated(setup):
    with patch.object(stripe.Customer, "retrieve", return_value=SimpleNamespace(id="cus_old", deleted=True)), \
         patch.object(stripe.Customer, "create", return_value=SimpleNamespace(id="cus_new")):
        assert billing.get_or_create_stripe_customer("u1", None) == "cus_new"
    assert setup == ["cus_new"]


def test_other_retrieve_error_returns_none(setup):
    with patch.object(stripe.Customer, "retrieve", side_effect=stripe.APIConnectionError("down")), \
         patch.object(stripe.Customer, "create") as create:
        assert billing.get_or_create_stripe_customer("u1", None) is None
    create.assert_not_called()
