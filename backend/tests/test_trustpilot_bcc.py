"""Trustpilot invites: customer emails BCC TRUSTPILOT_BCC, and the one-time check-in after the 3rd scan."""
from unittest.mock import MagicMock, patch

import pytest

from services import notifications

BCC = "invites@example.invalid"


class _SyncThread:
    """Run fire-and-forget senders inline so the test can read the request."""

    def __init__(self, target, args=(), daemon=None):
        self._target, self._args = target, args

    def start(self):
        self._target(*self._args)


@pytest.fixture
def post(monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "re_test")
    monkeypatch.setattr(notifications.threading, "Thread", _SyncThread)
    with patch("services.notifications.httpx.post", return_value=MagicMock(status_code=200)) as mock:
        yield mock


def _json(post):
    return post.call_args.kwargs["json"]


@pytest.mark.parametrize("send", [
    lambda: notifications.send_spreadsheet_email("a@example.com", b"x,y"),
    lambda: notifications.send_paid_welcome_email("a@example.com", "https://link"),
    lambda: notifications.send_checkin_email("a@example.com", "Ann Lee", 3),
])
def test_customer_emails_bcc_trustpilot_when_set(post, monkeypatch, send):
    monkeypatch.setenv("TRUSTPILOT_BCC", BCC)
    send()
    assert _json(post)["bcc"] == [BCC]


def test_no_bcc_when_unset(post, monkeypatch):
    monkeypatch.delenv("TRUSTPILOT_BCC", raising=False)
    notifications.send_checkin_email("a@example.com", None, 3)
    assert "bcc" not in _json(post)


def test_checkin_greets_by_name_and_offers_g2(post):
    notifications.send_checkin_email("a@example.com", 'Ann "<b>" Lee', 3)
    body = _json(post)
    assert body["to"] == ['"Ann b Lee" <a@example.com>']
    assert "Hi Ann," in body["text"] and "g2.com" in body["text"]
    assert "<b>" not in body["html"]


def test_team_notifications_never_bcc(post, monkeypatch):
    monkeypatch.setenv("TRUSTPILOT_BCC", BCC)
    notifications._send("subject", "text")
    assert "bcc" not in _json(post)


@pytest.mark.parametrize("state,sent", [((None, 3), True), ((None, 2), False), ((None, 4), False), (("pending", 3), False)])
def test_checkin_only_on_third_scan_without_claim(state, sent):
    import main

    with patch("main.get_review_prompt_state", return_value=state), patch("main.send_checkin_email") as send:
        main._maybe_send_checkin("u1", {"email": "a@example.com", "full_name": "Ann"})
    assert send.called is sent


def test_checkin_never_breaks_scan():
    import main

    with patch("main.get_review_prompt_state", side_effect=RuntimeError("db")), patch("main.send_checkin_email") as send:
        main._maybe_send_checkin("u1", {"email": "a@example.com"})
    send.assert_not_called()
