"""Tests for the review reward: POST /api/review-claim and review_claim in /api/usage."""
from unittest.mock import patch

import pytest


@pytest.fixture
def deps():
    with patch("main.create_review_claim", return_value=True) as create, patch("main.notify_team") as notify, patch(
        "main.get_auth_user", return_value={"email": "scott@example.com", "full_name": "Scott"}
    ):
        yield {"create": create, "notify": notify}


def test_claim_recorded_and_team_notified(client, deps):
    r = client.post("/api/review-claim", json={"platform": "g2", "proof": "  https://www.g2.com/review/123 "})
    assert r.status_code == 200 and r.json()["status"] == "pending"
    deps["create"].assert_called_once_with("test-user-id", "g2", "https://www.g2.com/review/123")
    subject, text = deps["notify"].call_args.args
    assert "scott@example.com" in subject
    assert "grant_review_reward.py test-user-id" in text


def test_second_claim_rejected(client, deps):
    deps["create"].return_value = False
    assert client.post("/api/review-claim", json={"proof": "Scott T."}).status_code == 409
    deps["notify"].assert_not_called()


@pytest.mark.parametrize("body", [{"proof": ""}, {"proof": "x" * 501}, {"platform": "trustpilot", "proof": "Scott"}])
def test_invalid_claims_rejected(client, deps, body):
    assert client.post("/api/review-claim", json=body).status_code == 422
    deps["create"].assert_not_called()


def test_whitespace_proof_rejected(client, deps):
    assert client.post("/api/review-claim", json={"proof": "    "}).status_code == 400
    deps["create"].assert_not_called()


def test_claim_requires_login(deps):
    from fastapi.testclient import TestClient
    from main import app

    with TestClient(app) as c:
        assert c.post("/api/review-claim", json={"proof": "Scott"}).status_code == 401
    deps["create"].assert_not_called()


def test_notification_failure_still_ok(client, deps):
    deps["notify"].side_effect = RuntimeError("smtp down")
    assert client.post("/api/review-claim", json={"proof": "Scott"}).status_code == 200


def test_usage_reports_claim_status(client, no_db_review_claim):
    no_db_review_claim.return_value = "pending"
    with patch("main.ensure_free_grant", return_value={"free_pages": 40}):
        assert client.get("/api/usage").json()["review_claim"] == "pending"


def test_usage_survives_claim_lookup_failure(client, no_db_review_claim):
    from main import _review_claim_status

    with patch("main.get_review_claim_status", side_effect=RuntimeError("no table")):
        assert _review_claim_status("u") == "unknown"
