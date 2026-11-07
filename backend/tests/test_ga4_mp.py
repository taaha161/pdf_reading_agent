"""Tests for GA4 Measurement Protocol subscribe/purchase events from Stripe webhooks."""
from unittest.mock import patch

from services import billing, ga4_mp
from services.ga4_mp import build_payload, track_event


def test_build_payload_uses_browser_ids():
    p = build_payload("user-1", "purchase", {"value": 10.0, "x": None}, "123.456", "1700000000")
    assert p["client_id"] == "123.456"
    assert p["user_id"] == "user-1"
    ev = p["events"][0]
    assert ev["name"] == "purchase"
    assert ev["params"] == {"value": 10.0, "session_id": 1700000000, "engagement_time_msec": 1}


def test_build_payload_falls_back_to_stable_client_id():
    a = build_payload("user-1", "subscribe", {})["client_id"]
    assert a == build_payload("user-1", "subscribe", {})["client_id"]
    assert "." in a
    assert "session_id" not in build_payload("user-1", "subscribe", {}, None, "not-a-number")["events"][0]["params"]


def test_track_noop_without_secret(monkeypatch):
    monkeypatch.delenv("GA4_API_SECRET", raising=False)
    with patch.object(ga4_mp.threading, "Thread") as thread:
        track_event("user-1", "purchase", {})
    thread.assert_not_called()


def test_track_dispatches_with_secret(monkeypatch):
    monkeypatch.setenv("GA4_API_SECRET", "s")
    with patch.object(ga4_mp.threading, "Thread") as thread:
        track_event("user-1", "purchase", {"value": 1})
    assert thread.call_args.kwargs["args"][0]["events"][0]["name"] == "purchase"
    thread.return_value.start.assert_called_once()


def _invoice(billing_reason, amount=1000, meta=None):
    return {"data": {"object": {
        "id": "in_1", "billing_reason": billing_reason, "customer": "cus_1", "subscription": "sub_1",
        "customer_email": "j@example.com", "amount_paid": amount, "currency": "usd",
        "parent": {"subscription_details": {"metadata": meta or {}}},
    }}}


def _paid(event):
    with patch.object(billing, "_user_id_from_customer", return_value="user-1"), \
         patch.object(billing, "set_balance"), patch.object(billing, "set_stripe_ids"), \
         patch.object(billing, "track_subscription_purchase"), patch.object(billing, "track_event") as track:
        ok, _ = billing._handle_invoice_paid(event)
    assert ok
    return track


def test_first_invoice_sends_purchase_with_ga_ids():
    track = _paid(_invoice("subscription_create", meta={"ga_client_id": "1.2", "ga_session_id": "99"}))
    user_id, name, params, client_id, session_id = track.call_args.args
    assert (user_id, name, client_id, session_id) == ("user-1", "purchase", "1.2", "99")
    assert params["transaction_id"] == "in_1"
    assert params["value"] == 10.0
    assert params["payment_type"] == "subscription_first"


def test_renewal_sends_renewal_purchase():
    track = _paid(_invoice("subscription_cycle"))
    assert track.call_args.args[2]["payment_type"] == "subscription_renewal"


def test_zero_amount_trial_invoice_sends_no_purchase():
    _paid(_invoice("subscription_create", amount=0)).assert_not_called()


def test_subscription_checkout_sends_subscribe():
    session = {"id": "cs_1", "mode": "subscription", "amount_total": 0, "currency": "usd",
               "metadata": {"user_id": "user-1", "ga_client_id": "1.2"}}
    with patch.object(billing, "track_event") as track:
        ok, _ = billing._handle_checkout_completed({"data": {"object": session}})
    assert ok
    user_id, name, params, client_id, _ = track.call_args.args
    assert (user_id, name, client_id, params["trial"]) == ("user-1", "subscribe", "1.2", "yes")


def test_topup_checkout_sends_purchase():
    session = {"id": "cs_2", "mode": "payment", "amount_total": 1000, "currency": "usd",
               "metadata": {"user_id": "user-1", "topup": "1"}}
    with patch.object(billing, "add_balance"), patch.object(billing, "track_event") as track:
        ok, _ = billing._handle_checkout_completed({"data": {"object": session}})
    assert ok
    assert track.call_args.args[2]["payment_type"] == "topup"


def test_ga4_failure_never_fails_webhook():
    with patch.object(billing, "track_event", side_effect=RuntimeError("boom")):
        billing._track_ga4("user-1", "purchase", {}, {})
