"""Paid signup: pay first (guest Stripe Checkout), account created after payment."""
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from services import billing, paid_signup

NOW = datetime.now(timezone.utc)
# Dummy values for the password rules, not real credentials.
STRONG_PW = "Good#Pass1"  # ggignore
WEAK_PW = "weak"  # ggignore


def _user(uid="u1", email="new@example.com", customer="cus_new", has_password=False, age=timedelta(minutes=5)):
    return {"id": uid, "email": email, "created_at": NOW - age, "has_password": has_password,
            "paid_signup_customer": customer}


def _resp(status, body=None):
    r = MagicMock(status_code=status, text="")
    r.json.return_value = body or {}
    return r


@pytest.fixture
def side_effects():
    with patch.object(paid_signup, "mark_free_grant_used") as mark, \
         patch.object(paid_signup, "claim_referral") as claim, \
         patch.object(paid_signup, "set_stripe_ids") as set_ids, \
         patch.object(paid_signup, "get_billing", return_value=None), \
         patch.object(paid_signup, "notify_signup"), \
         patch.object(paid_signup, "notify_team") as team, \
         patch.object(paid_signup, "_send_welcome") as welcome:
        yield {"mark": mark, "claim": claim, "set_ids": set_ids, "team": team, "welcome": welcome}


# --- ensure_account ---

def test_new_email_creates_confirmed_account_without_free_month(side_effects):
    created = _user()
    with patch.object(paid_signup, "get_user_id_by_stripe_customer_id", return_value=None), \
         patch.object(paid_signup, "get_auth_user", side_effect=[None, created]), \
         patch.object(paid_signup, "_admin", return_value=_resp(200, {"id": "u1"})) as admin:
        acct = paid_signup.ensure_account("cus_new", "new@example.com", "hassan20", "Jane Doe")
    assert acct == {"user_id": "u1", "created_here": True, "existing_account": False}
    body = admin.call_args.args[2]
    assert body["email_confirm"] is True
    assert body["user_metadata"]["paid_signup_customer"] == "cus_new"
    assert body["user_metadata"]["full_name"] == "Jane Doe"
    side_effects["set_ids"].assert_called_once_with("u1", "cus_new", None)
    side_effects["mark"].assert_called_once_with("u1")  # no free month for paid signups
    side_effects["claim"].assert_called_once_with("u1", "hassan20")
    side_effects["welcome"].assert_called_once_with("new@example.com")


def test_repeat_event_is_idempotent(side_effects):
    """Customer already linked: no second account, no second welcome email."""
    with patch.object(paid_signup, "get_user_id_by_stripe_customer_id", return_value="u1"), \
         patch.object(paid_signup, "get_auth_user", return_value=_user()), \
         patch.object(paid_signup, "_admin") as admin:
        acct = paid_signup.ensure_account("cus_new", "new@example.com")
    assert acct["created_here"] is True
    admin.assert_not_called()
    side_effects["welcome"].assert_not_called()
    side_effects["set_ids"].assert_not_called()


def test_existing_email_attaches_subscription_but_is_not_created_here(side_effects):
    existing = _user(uid="old", email="me@example.com", customer=None, has_password=True, age=timedelta(days=90))
    with patch.object(paid_signup, "get_user_id_by_stripe_customer_id", return_value=None), \
         patch.object(paid_signup, "get_auth_user", return_value=existing), \
         patch.object(paid_signup, "_admin") as admin:
        acct = paid_signup.ensure_account("cus_new", "ME@example.com", "hassan20")
    assert acct == {"user_id": "old", "created_here": False, "existing_account": True}
    admin.assert_not_called()
    side_effects["set_ids"].assert_called_once_with("old", "cus_new", None)
    side_effects["mark"].assert_not_called()  # an existing account keeps whatever it had
    side_effects["claim"].assert_not_called()


def test_racing_create_finds_the_account(side_effects):
    """Two events at once: the loser's create gets 422 and re-reads by email."""
    created = _user()
    with patch.object(paid_signup, "get_user_id_by_stripe_customer_id", return_value=None), \
         patch.object(paid_signup, "get_auth_user", side_effect=[None, created]), \
         patch.object(paid_signup, "_admin", return_value=_resp(422)):
        acct = paid_signup.ensure_account("cus_new", "new@example.com")
    assert acct["user_id"] == "u1" and acct["created_here"] is True
    side_effects["welcome"].assert_not_called()


def test_no_email_yet_returns_none(side_effects):
    with patch.object(paid_signup, "get_user_id_by_stripe_customer_id", return_value=None), \
         patch.object(paid_signup.stripe.Customer, "retrieve", return_value={"email": None}):
        assert paid_signup.ensure_account("cus_new") is None


def test_second_subscription_notifies_team(side_effects):
    existing = _user(uid="old", customer=None, has_password=True)
    with patch.object(paid_signup, "get_user_id_by_stripe_customer_id", return_value=None), \
         patch.object(paid_signup, "get_auth_user", return_value=existing), \
         patch.object(paid_signup, "get_billing", return_value={"stripe_customer_id": "cus_old", "stripe_subscription_id": "sub_old"}):
        paid_signup.ensure_account("cus_new", "new@example.com")
    side_effects["team"].assert_called_once()


# --- password ---

@pytest.mark.parametrize("user,ok", [
    (_user(), True),
    (_user(has_password=True), False),                 # once only
    (_user(customer="cus_other"), False),              # someone else's checkout
    (_user(customer=None), False),                     # pre-existing account with that email
    (_user(age=timedelta(hours=25)), False),           # too late
    (None, False),
])
def test_password_allowed(user, ok):
    assert paid_signup._password_allowed(user, "cus_new") is ok


@pytest.mark.parametrize("pw,ok", [("Short1!", False), ("alllower1!", False), ("NoNumber!!", False),
                                   ("NoSpecial11", False), (STRONG_PW, True)])
def test_password_rules(pw, ok):
    assert (paid_signup.password_problem(pw) is None) is ok


def _session(status="complete", payment="paid", flow="paid_signup", customer="cus_new"):
    return {"id": "cs_1", "status": status, "payment_status": payment, "customer": customer,
            "metadata": {"flow": flow}, "customer_details": {"email": "new@example.com", "name": None},
            "amount_total": 750, "currency": "usd"}


def test_set_initial_password_on_created_account():
    with patch.object(paid_signup.stripe.checkout.Session, "retrieve", return_value=_session()), \
         patch.object(paid_signup, "ensure_account", return_value={"user_id": "u1", "created_here": True, "existing_account": False}), \
         patch.object(paid_signup, "get_auth_user", return_value=_user()), \
         patch.object(paid_signup, "_admin", return_value=_resp(200)) as admin:
        assert paid_signup.set_initial_password("cs_1", STRONG_PW) == "new@example.com"
    assert admin.call_args.args[:2] == ("PUT", "users/u1")


def test_set_initial_password_refuses_existing_account():
    existing = _user(uid="old", customer=None, has_password=False)  # e.g. Google-only account
    with patch.object(paid_signup.stripe.checkout.Session, "retrieve", return_value=_session()), \
         patch.object(paid_signup, "ensure_account", return_value={"user_id": "old", "created_here": False, "existing_account": True}), \
         patch.object(paid_signup, "get_auth_user", return_value=existing), \
         patch.object(paid_signup, "_admin") as admin:
        with pytest.raises(paid_signup.PasswordError):
            paid_signup.set_initial_password("cs_1", STRONG_PW)
    admin.assert_not_called()


def test_set_initial_password_rejects_weak_password_before_stripe():
    with patch.object(paid_signup.stripe.checkout.Session, "retrieve") as retrieve:
        with pytest.raises(paid_signup.PasswordError):
            paid_signup.set_initial_password("cs_1", WEAK_PW)
    retrieve.assert_not_called()


# --- session status ---

@pytest.mark.parametrize("session,status", [
    (_session(flow="other"), "invalid"),
    (_session(status="open", payment="unpaid"), "pending"),
])
def test_session_status_not_ready(session, status):
    with patch.object(paid_signup.stripe.checkout.Session, "retrieve", return_value=session):
        assert paid_signup.session_status("cs_1")["status"] == status


def test_session_status_rejects_non_session_ids():
    assert paid_signup.session_status("../../etc")["status"] == "invalid"


def test_session_status_ready():
    with patch.object(paid_signup.stripe.checkout.Session, "retrieve", return_value=_session()), \
         patch.object(paid_signup, "ensure_account", return_value={"user_id": "u1", "created_here": True, "existing_account": False}), \
         patch.object(paid_signup, "get_auth_user", return_value=_user()):
        st = paid_signup.session_status("cs_1")
    assert st["status"] == "ready" and st["needs_password"] is True and st["existing_account"] is False
    assert st["email"] == "new@example.com"


# --- checkout ---

def test_guest_checkout_applies_referral_coupon():
    aff = {"id": "a1", "active": True, "discount_pct": 25, "discount_months": 3, "stripe_coupon_id": "co_1"}
    with patch.object(billing, "_stripe_available", return_value=True), \
         patch.object(paid_signup, "get_affiliate_by_code", return_value=aff), \
         patch.object(paid_signup.stripe.checkout.Session, "create", return_value=MagicMock(url="https://stripe/x", id="cs_1")) as create:
        out = paid_signup.create_guest_checkout("HASSAN20")
    assert out == {"url": "https://stripe/x", "sessionId": "cs_1"}
    kw = create.call_args.kwargs
    assert kw["mode"] == "subscription" and "customer" not in kw
    assert kw["discounts"] == [{"coupon": "co_1"}] and "allow_promotion_codes" not in kw
    assert kw["metadata"]["flow"] == "paid_signup" and kw["metadata"]["referral_code"] == "hassan20"
    assert kw["subscription_data"]["metadata"]["flow"] == "paid_signup"
    assert "/welcome?session_id={CHECKOUT_SESSION_ID}" in kw["success_url"]


def test_guest_checkout_without_code_allows_promo_codes():
    with patch.object(billing, "_stripe_available", return_value=True), \
         patch.object(paid_signup.stripe.checkout.Session, "create", return_value=MagicMock(url="u", id="cs")) as create:
        paid_signup.create_guest_checkout(None)
    kw = create.call_args.kwargs
    assert kw["allow_promotion_codes"] is True and "referral_code" not in kw["metadata"]


# --- webhooks ---

def _invoice_event():
    return {"data": {"object": {
        "id": "in_1", "billing_reason": "subscription_create", "customer": "cus_new",
        "customer_email": "new@example.com", "amount_paid": 750, "currency": "usd",
        "parent": {"subscription_details": {"subscription": "sub_1", "metadata": {"flow": "paid_signup", "referral_code": "hassan20"}}},
    }}}


def test_invoice_before_checkout_event_creates_account_and_sets_plan():
    with patch.object(billing, "get_user_id_by_stripe_customer_id", return_value=None), \
         patch.object(paid_signup, "ensure_account", return_value={"user_id": "u1", "created_here": True, "existing_account": False}) as ensure, \
         patch.object(billing, "set_plan_pages") as plan, \
         patch.object(billing, "set_stripe_ids"), \
         patch.object(billing, "record_affiliate_payment") as commission, \
         patch.object(billing, "track_subscription_purchase"), \
         patch.object(billing, "_track_ga4"):
        ok, _ = billing._handle_invoice_paid(_invoice_event())
    assert ok
    ensure.assert_called_once_with("cus_new", "new@example.com", "hassan20", None)
    plan.assert_called_once_with("u1", billing.PLAN_PAGES)
    commission.assert_called_once()


def test_invoice_asks_stripe_to_retry_when_account_not_ready():
    with patch.object(billing, "get_user_id_by_stripe_customer_id", return_value=None), \
         patch.object(paid_signup, "ensure_account", return_value=None), \
         patch.object(billing, "set_plan_pages") as plan:
        ok, _ = billing._handle_invoice_paid(_invoice_event())
    assert not ok
    plan.assert_not_called()
