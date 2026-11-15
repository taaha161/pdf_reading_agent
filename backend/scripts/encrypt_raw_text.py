"""Encrypt existing plaintext job_payloads.raw_text (and re-encrypt with the newest key after rotation).

Usage (from backend/, with DATABASE_URL and DATA_ENCRYPTION_KEY set):
  python scripts/encrypt_raw_text.py            # dry run: counts only
  python scripts/encrypt_raw_text.py --apply    # write changes

Idempotent; safe to re-run. Commits in batches.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

import psycopg2  # noqa: E402

from services.field_crypto import PREFIX, _fernet, decrypt_text, encrypt_text  # noqa: E402

BATCH = 200


def main(apply: bool) -> None:
    f = _fernet()
    if f is None:
        sys.exit("DATA_ENCRYPTION_KEY is not set")
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    done = skipped = 0
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT job_id FROM job_payloads WHERE raw_text IS NOT NULL AND raw_text <> ''")
            ids = [r[0] for r in cur.fetchall()]
        for i in range(0, len(ids), BATCH):
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT job_id, raw_text FROM job_payloads WHERE job_id = ANY(%s::uuid[]) FOR UPDATE",
                    ([str(x) for x in ids[i : i + BATCH]],),
                )
                for job_id, raw in cur.fetchall():
                    if raw.startswith(PREFIX):
                        # Re-encrypt under the first (newest) key; no-op for data already on it.
                        token = raw[len(PREFIX):].encode("ascii")
                        new = PREFIX + f.rotate(token).decode("ascii")
                        if new == raw:
                            skipped += 1
                            continue
                    else:
                        new = encrypt_text(raw)
                    assert decrypt_text(new) == (decrypt_text(raw) if raw.startswith(PREFIX) else raw)
                    if apply:
                        cur.execute("UPDATE job_payloads SET raw_text = %s WHERE job_id = %s", (new, job_id))
                    done += 1
            if apply:
                conn.commit()
            else:
                conn.rollback()
    finally:
        conn.close()
    print(f"{'encrypted' if apply else 'would encrypt'}: {done}, rows total: {len(ids)}")


if __name__ == "__main__":
    main("--apply" in sys.argv)
