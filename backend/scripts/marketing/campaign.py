"""Tax season 2027 marketing broadcast via Resend.

Run these steps in order from backend/ (each one is safe to re-run):

  python -m scripts.marketing.campaign audience            # dry run: count who would get it
  python -m scripts.marketing.campaign sync                # upsert contacts into the Resend segment
  python -m scripts.marketing.campaign tracking            # turn on open + click tracking for the sender domain
  python -m scripts.marketing.campaign test you@example.com  # send one copy to yourself
  python -m scripts.marketing.campaign draft               # create the broadcast as a DRAFT in Resend
  python -m scripts.marketing.campaign send <broadcast_id> # actually send it (asks for confirmation)

Audience:
  * Signed-up users (paying and free): Supabase auth.users, confirmed email, not deleted.
  * "Send to your inbox" leads: email_captures rows with marketing_opt_in = true ONLY.
    Leads who did not tick the box are excluded, as the privacy policy promises.

Env (backend/.env):
  RESEND_API_KEY            required
  DATABASE_URL              required for audience/sync
  MARKETING_POSTAL_ADDRESS  required for test/draft (CAN-SPAM footer)
  MARKETING_FROM            default "Bank Statement Scanner <hello@bankstatementscanner.com>"
  MARKETING_REPLY_TO        default team@bankstatementscanner.com
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import httpx
import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor

HERE = Path(__file__).resolve().parent
load_dotenv(HERE.parent.parent / ".env")

API = "https://api.resend.com"
CAMPAIGN = "tax_season_2027"
SEGMENT_NAME = "Tax season 2027"
SUBJECT = "Tax season is coming. Your bank statements are ready when you are 📊"
HTML_FILE = HERE / f"{CAMPAIGN}.html"
TEXT_FILE = HERE / f"{CAMPAIGN}.txt"

SIGNUPS_SQL = """
SELECT DISTINCT lower(trim(u.email)) AS email,
       (b.stripe_subscription_id IS NOT NULL) AS paying
FROM auth.users u
LEFT JOIN user_billing b ON b.user_id = u.id::text
WHERE u.email IS NOT NULL
  AND u.email_confirmed_at IS NOT NULL
  AND u.deleted_at IS NULL
  AND COALESCE(u.is_anonymous, false) = false
"""

LEADS_SQL = """
SELECT DISTINCT lower(trim(email)) AS email
FROM email_captures
WHERE marketing_opt_in = true AND email IS NOT NULL
"""


# ---------- helpers ----------

def _key() -> str:
    key = os.environ.get("RESEND_API_KEY", "").strip()
    if not key:
        sys.exit("RESEND_API_KEY is not set in backend/.env")
    return key


def _api(method: str, path: str, json: dict | None = None) -> httpx.Response:
    """Resend call with simple backoff on rate limits (default limit is a few req/s)."""
    for attempt in range(5):
        resp = httpx.request(
            method, f"{API}{path}", json=json, timeout=20.0,
            headers={"Authorization": f"Bearer {_key()}"},
        )
        if resp.status_code != 429:
            time.sleep(0.6)  # stay under the per-second limit
            return resp
        time.sleep(2 ** attempt)
    return resp


def _render(fmt: str) -> str:
    address = os.environ.get("MARKETING_POSTAL_ADDRESS", "").strip()
    if not address:
        sys.exit("Set MARKETING_POSTAL_ADDRESS in backend/.env (a postal address is required in marketing email under CAN-SPAM).")
    body = (HTML_FILE if fmt == "html" else TEXT_FILE).read_text()
    return body.replace("{{POSTAL_ADDRESS}}", address)


def _from() -> str:
    return os.environ.get("MARKETING_FROM", "Bank Statement Scanner <hello@bankstatementscanner.com>").strip()


def _reply_to() -> str:
    return os.environ.get("MARKETING_REPLY_TO", "team@bankstatementscanner.com").strip()


def _audience() -> tuple[dict[str, str], dict[str, int]]:
    """Return {email: tag} where tag is paid | free | lead, plus counts. Signup records win over lead."""
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        sys.exit("DATABASE_URL is not set in backend/.env")
    with psycopg2.connect(url, cursor_factory=RealDictCursor) as conn, conn.cursor() as cur:
        cur.execute(SIGNUPS_SQL)
        signups = cur.fetchall()
        cur.execute(LEADS_SQL)
        leads = cur.fetchall()

    people: dict[str, str] = {}
    for r in leads:
        people[r["email"]] = "lead"
    for r in signups:
        # A user may have several billing rows in theory; paid wins.
        if people.get(r["email"]) != "paid":
            people[r["email"]] = "paid" if r["paying"] else "free"
    counts = {t: sum(1 for v in people.values() if v == t) for t in ("paid", "free", "lead")}
    return people, counts


def _segment_id(create: bool) -> str | None:
    resp = _api("GET", "/segments")
    resp.raise_for_status()
    for seg in resp.json().get("data", []):
        if seg.get("name") == SEGMENT_NAME:
            return seg["id"]
    if not create:
        return None
    resp = _api("POST", "/segments", {"name": SEGMENT_NAME})
    resp.raise_for_status()
    return resp.json()["id"]


# ---------- commands ----------

def cmd_audience(_args) -> None:
    people, counts = _audience()
    print(f"Would email {len(people)} unique addresses:")
    for tag, n in counts.items():
        print(f"  {tag:>5}: {n}")


def cmd_sync(_args) -> None:
    people, counts = _audience()
    seg = _segment_id(create=True)
    print(f"Segment '{SEGMENT_NAME}' = {seg}. Syncing {len(people)} contacts {counts} ...")
    created = existing = failed = 0
    for i, email in enumerate(sorted(people), 1):
        # Never send "unsubscribed": false, so anyone who unsubscribed earlier stays unsubscribed.
        resp = _api("POST", "/contacts", {"email": email})
        if resp.status_code < 300:
            created += 1
        elif resp.status_code in (409, 422) or "exist" in resp.text.lower():
            existing += 1
        else:
            failed += 1
            print(f"  ! create {email}: {resp.status_code} {resp.text[:200]}")
            continue
        add = _api("POST", f"/contacts/{email}/segments/{seg}")
        if add.status_code >= 300 and "already" not in add.text.lower():
            failed += 1
            print(f"  ! segment {email}: {add.status_code} {add.text[:200]}")
        if i % 50 == 0:
            print(f"  {i}/{len(people)}")
    print(f"Done. created={created} already_existed={existing} failed={failed}")


def cmd_tracking(_args) -> None:
    sender_domain = _from().split("@")[-1].rstrip(">").strip()
    resp = _api("GET", "/domains")
    resp.raise_for_status()
    match = next((d for d in resp.json().get("data", []) if d.get("name") == sender_domain), None)
    if not match:
        sys.exit(f"Domain {sender_domain} is not in this Resend account. Verify it first, or change MARKETING_FROM.")
    resp = _api("PATCH", f"/domains/{match['id']}", {
        "open_tracking": True, "click_tracking": True, "tracking_subdomain": "links",
    })
    print(resp.status_code, resp.text)
    print("\nIf a 'Tracking' CNAME record is listed above, add it at your DNS provider, then re-verify the domain in Resend.")


def cmd_test(args) -> None:
    html = _render("html").replace("{{{RESEND_UNSUBSCRIBE_URL}}}", "https://bankstatementscanner.com")
    text = _render("text").replace("{{{RESEND_UNSUBSCRIBE_URL}}}", "https://bankstatementscanner.com")
    resp = _api("POST", "/emails", {
        "from": _from(), "to": [args.to], "reply_to": _reply_to(),
        "subject": f"[TEST] {SUBJECT}", "html": html, "text": text,
        "tags": [{"name": "campaign", "value": CAMPAIGN}],
    })
    print(resp.status_code, resp.text)


def cmd_draft(_args) -> None:
    seg = _segment_id(create=False)
    if not seg:
        sys.exit("Segment not found. Run `sync` first.")
    resp = _api("POST", "/broadcasts", {
        "segment_id": seg,
        "name": "Tax season 2027",
        "from": _from(),
        "reply_to": _reply_to(),
        "subject": SUBJECT,
        "html": _render("html"),
        "text": _render("text"),
    })
    print(resp.status_code, resp.text)
    if resp.status_code < 300:
        print(f"\nDraft created. Review it in the Resend dashboard, then:\n  python -m scripts.marketing.campaign send {resp.json()['id']}")


def cmd_send(args) -> None:
    confirm = input(f"Send broadcast {args.broadcast_id} to every contact in '{SEGMENT_NAME}'? This cannot be undone. Type SEND: ")
    if confirm.strip() != "SEND":
        sys.exit("Aborted.")
    resp = _api("POST", f"/broadcasts/{args.broadcast_id}/send", {})
    print(resp.status_code, resp.text)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("audience").set_defaults(fn=cmd_audience)
    sub.add_parser("sync").set_defaults(fn=cmd_sync)
    sub.add_parser("tracking").set_defaults(fn=cmd_tracking)
    t = sub.add_parser("test"); t.add_argument("to"); t.set_defaults(fn=cmd_test)
    sub.add_parser("draft").set_defaults(fn=cmd_draft)
    s = sub.add_parser("send"); s.add_argument("broadcast_id"); s.set_defaults(fn=cmd_send)
    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
