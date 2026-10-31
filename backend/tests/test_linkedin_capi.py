"""Tests for LinkedIn Conversions API subscription purchase tracking."""
import hashlib
from unittest.mock import patch

from services import billing, linkedin_capi
from services.linkedin_capi import build_event, track_subscription_purchase


def test_build_event_hashes_email_and_sets_value():
    event = build_event("123", "  Jane@Example.com ", "in_1", 1700000000000, 1000, "usd")
    assert event["conversion"] == "urn:lla:llaPartnerConversion:123"
    assert event["conversionHappenedAt"] == 1700000000000
    assert event["eventId"] == "in_1"
    assert event["conversionValue"] == {"currencyCode": "USD", "amount": "10.00"}
    expected = hashlib.sha256(b"jane@example.com").hexdigest()
    assert event["user"]["userIds"] == [{"idType": "SHA256_EMAIL", "idValue": expected}]


def test_track_noop_without_config(monkeypatch):
    monkeypatch.delenv("LINKEDIN_CAPI_TOKEN", raising=False)
    monkeypatch.setenv("LINKEDIN_PURCHASE_CONVERSION_ID", "123")
    with patch.object(linkedin_capi.threading, "Thread") as thread:
        track_subscription_purchase("jane@example.com", "in_1", 1000, "usd")
    thread.assert_not_called()


def test_track_dispatches_when_configured(monkeypatch):
    monkeypatch.setenv("LINKEDIN_CAPI_TOKEN", "tok")
    monkeypatch.setenv("LINKEDIN_PURCHASE_CONVERSION_ID", "123")
    with patch.object(linkedin_capi.threading, "Thread") as thread:
        track_subscription_purchase("jane@example.com", "in_1", 1000, "usd")
    event = thread.call_args.kwargs["args"][0]
    assert event["eventId"] == "in_1"
    thread.return_value.start.assert_called_once()


def _invoice_event(billing_reason):
    invoice = {
        "id": "in_1",
        "billing_reason": billing_reason,
        "customer": "cus_1",
        "subscription": "sub_1",
        "customer_email": "jane@example.com",
        "amount_paid": 1000,
        "currency": "usd",
    }
    return {"data": {"object": invoice}}


def _handle(billing_reason):
    with patch.object(billing, "_user_id_from_customer", return_value="user-1"), patch.object(
        billing, "set_balance"
    ), patch.object(billing, "set_stripe_ids"), patch.object(billing, "track_subscription_purchase") as track:
        ok, _ = billing._handle_invoice_paid(_invoice_event(billing_reason))
    assert ok
    return track


def test_first_subscription_invoice_tracks_purchase():
    track = _handle("subscription_create")
    track.assert_called_once_with(email="jane@example.com", event_id="in_1", amount_cents=1000, currency="usd")


def test_renewal_invoice_does_not_track():
    _handle("subscription_cycle").assert_not_called()
