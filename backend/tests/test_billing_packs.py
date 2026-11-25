"""Which page packs a user may buy: small packs for subscribers, a bulk pack for everyone else."""
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import stripe

from services import billing


@pytest.mark.parametrize("pack", ["10", "30", "100", "450"])
def test_subscriber_can_buy_any_pack(pack):
    assert billing.resolve_pack(pack, subscribed=True) == pack


def test_subscriber_unknown_pack_falls_back_to_default():
    assert billing.resolve_pack("nope", subscribed=True) == billing.DEFAULT_PACK
    assert billing.resolve_pack(None, subscribed=True) == billing.DEFAULT_PACK


@pytest.mark.parametrize("pack", ["10", "30", "100"])
def test_non_subscriber_cannot_buy_small_packs(pack):
    with pytest.raises(billing.PackNotAllowed):
        billing.resolve_pack(pack, subscribed=False)


@pytest.mark.parametrize("pack", ["450", None, "nope"])
def test_non_subscriber_gets_bulk_pack(pack):
    assert billing.resolve_pack(pack, subscribed=False) == billing.BULK_PACK_ID


def test_bulk_pack_price():
    assert billing.PAGE_PACKS[billing.BULK_PACK_ID] == (450, 4999)


@pytest.fixture
def stripe_ready(monkeypatch):
    monkeypatch.setattr(billing, "_STRIPE_KEY", "sk_test")
    monkeypatch.setattr(billing, "get_or_create_stripe_customer", lambda uid, email: "cus_1")
    monkeypatch.setattr(billing, "_referral_discount", lambda uid: None)


def _checkout(monkeypatch, sub_id, pack):
    monkeypatch.setattr(billing, "get_billing", lambda uid: {"stripe_subscription_id": sub_id})
    with patch.object(stripe.checkout.Session, "create", return_value=SimpleNamespace(url="u", id="cs")) as create:
        billing.create_checkout_session("user-1", "topup", pack=pack)
    return create.call_args.kwargs


def test_checkout_bulk_pack_for_non_subscriber(stripe_ready, monkeypatch):
    kw = _checkout(monkeypatch, None, "450")
    assert kw["line_items"][0]["price_data"]["unit_amount"] == 4999
    assert kw["metadata"]["pack"] == "450"
    assert kw["metadata"]["pack_pages"] == "450"


def test_checkout_small_pack_for_subscriber(stripe_ready, monkeypatch):
    kw = _checkout(monkeypatch, "sub_1", "30")
    assert kw["line_items"][0]["price_data"]["unit_amount"] == 500


def test_checkout_small_pack_refused_without_subscription(stripe_ready, monkeypatch):
    monkeypatch.setattr(billing, "get_billing", lambda uid: {"stripe_subscription_id": None})
    with patch.object(stripe.checkout.Session, "create") as create, pytest.raises(billing.PackNotAllowed):
        billing.create_checkout_session("user-1", "topup", pack="30")
    create.assert_not_called()


# --- frozen subscriber packs ---
import store  # noqa: E402


def _row(sub_id, sub_pack=30, pack=5, plan=0):
    return {"stripe_subscription_id": sub_id, "sub_pack_pages": sub_pack, "pack_pages": pack, "plan_pages": plan,
            "free_pages": 0, "free_expires_at": None}


def test_subscriber_pack_pages_usable_while_subscribed():
    row = _row("sub_1")
    assert store.pages_available(row) == 35
    assert store.frozen_pages(row) == 0


def test_subscriber_pack_pages_frozen_after_cancel():
    row = _row(None)
    assert store.pages_available(row) == 5  # bulk/legacy pack pages only
    assert store.frozen_pages(row) == 30
