"""Grant (or reject) a pending review-reward claim.

Usage (from backend/, with DATABASE_URL set):
  python scripts/grant_review_reward.py --list            # pending claims
  python scripts/grant_review_reward.py <user_id|email>         # add 100 pack pages, mark granted
  python scripts/grant_review_reward.py <user_id|email> --reject
  python scripts/grant_review_reward.py <email> --proof "<review link>"   # review reported by email (no in-app claim)

Granting is one transaction and only acts on a pending claim, so re-running can't double-credit.
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

import store  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("user_id", nargs="?", help="user id, or the account's email address")
    ap.add_argument("--proof", help="review link/name for a review reported outside the app; records and grants the claim")
    ap.add_argument("--platform", default="g2", choices=["g2"])
    ap.add_argument("--reject", action="store_true", help="mark the claim rejected instead of granting")
    ap.add_argument("--list", action="store_true", help="list pending claims")
    args = ap.parse_args()

    if args.list or not args.user_id:
        with store._cursor() as cur:
            cur.execute(
                """
                SELECT c.user_id, u.email, c.platform, c.proof, c.created_at
                FROM review_claims c LEFT JOIN auth.users u ON u.id::text = c.user_id
                WHERE c.status = 'pending' ORDER BY c.created_at
                """
            )
            rows = cur.fetchall()
        for r in rows:
            print(" | ".join(str(x) for x in r))
        print(f"{len(rows)} pending")
        return 0

    user_id = args.user_id
    if "@" in user_id:
        with store._cursor() as cur:
            cur.execute("SELECT id::text FROM auth.users WHERE lower(email) = lower(%s)", (user_id,))
            row = cur.fetchone()
        if not row:
            print("no account with that email")
            return 1
        user_id = row[0]
    args.user_id = user_id

    if args.proof:
        ok = store.create_granted_review_claim(user_id, args.platform, args.proof.strip())
        print(f"granted {store.REVIEW_REWARD_PAGES} pack pages" if ok else "account already has a claim; nothing granted")
        return 0 if ok else 1

    if args.reject:
        ok = store.reject_review_claim(args.user_id)
        print("rejected" if ok else "no pending claim for that user")
    else:
        ok = store.grant_review_reward(args.user_id)
        print(f"granted {store.REVIEW_REWARD_PAGES} pack pages" if ok else "no pending claim for that user")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
