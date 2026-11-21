"""Read the printed summary box (statement_meta) for saved statements scanned before it existed.

Usage (from backend/, with DATABASE_URL, DATA_ENCRYPTION_KEY and GOOGLE_GEMINI_API_KEY set):
  python scripts/backfill_statement_meta.py             # dry run: counts only
  python scripts/backfill_statement_meta.py --apply     # read and save
  python scripts/backfill_statement_meta.py --apply --limit 50

Only payloads with statement_meta IS NULL and saved statement text are touched, so it's
idempotent and safe to re-run. One small Gemini call per statement, paced by --delay.
"""
from __future__ import annotations

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

import psycopg2  # noqa: E402

from services.field_crypto import decrypt_text  # noqa: E402
from services.statement_meta import extract_statement_meta, normalize_meta  # noqa: E402
from store import set_statement_meta  # noqa: E402


def main(apply: bool, limit: int | None, delay: float) -> None:
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT job_id FROM job_payloads WHERE statement_meta IS NULL "
                "AND raw_text IS NOT NULL AND raw_text <> '' ORDER BY job_id"
            )
            ids = [r[0] for r in cur.fetchall()]
    finally:
        conn.close()
    if limit:
        ids = ids[:limit]
    print(f"{len(ids)} saved statements without a summary")
    if not apply:
        print("Dry run. Re-run with --apply to read and save them.")
        return

    saved = unreadable = 0
    for n, job_id in enumerate(ids, start=1):
        conn = psycopg2.connect(os.environ["DATABASE_URL"])
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT raw_text, currency FROM job_payloads WHERE job_id = %s", (job_id,))
                row = cur.fetchone()
        finally:
            conn.close()
        if not row:  # purged meanwhile
            continue
        raw = extract_statement_meta(decrypt_text(row[0]) or "")
        if raw:
            set_statement_meta(str(job_id), normalize_meta(raw, row[1]))
            saved += 1
        else:
            unreadable += 1
        print(f"[{n}/{len(ids)}] {job_id}: {'saved' if raw else 'no summary read'}")
        time.sleep(delay)
    print(f"Done: {saved} saved, {unreadable} unreadable (left NULL, retried on the next run)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--apply", action="store_true", help="read and save (default: dry run)")
    parser.add_argument("--limit", type=int, default=None, help="at most this many statements")
    parser.add_argument("--delay", type=float, default=0.5, help="seconds between Gemini calls")
    args = parser.parse_args()
    main(args.apply, args.limit, args.delay)
