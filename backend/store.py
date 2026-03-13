"""Job store: DB-backed (Supabase Postgres). Jobs are scoped by user_id."""
import json
import os
import uuid
from contextlib import contextmanager
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

from services.csv_export import transactions_to_csv


def _get_conn():
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg2.connect(url, cursor_factory=RealDictCursor)


@contextmanager
def _cursor():
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def create_job_id() -> str:
    return str(uuid.uuid4())


def set_job(
    job_id: str,
    user_id: str,
    transactions: list[dict],
    csv_content: str,
    raw_text: str = "",
    currency: str | None = None,
    incognito: bool = False,
    conversion_mode: str | None = None,
) -> None:
    """Insert job for user; if not incognito, also insert payload (transactions, raw_text, currency)."""
    with _cursor() as cur:
        cur.execute(
            """
            INSERT INTO jobs (id, user_id, created_at, incognito, conversion_mode)
            VALUES (%s, %s, NOW(), %s, %s)
            """,
            (job_id, user_id, incognito, conversion_mode),
        )
        if not incognito:
            cur.execute(
                """
                INSERT INTO job_payloads (job_id, transactions, raw_text, currency)
                VALUES (%s, %s, %s, %s)
                """,
                (job_id, json.dumps(transactions), raw_text, currency),
            )


def list_jobs(user_id: str, limit: int = 100) -> list[dict]:
    """Return list of jobs for user: id, created_at, transaction_count, currency, conversion_mode. Newest first."""
    with _cursor() as cur:
        cur.execute(
            """
            SELECT j.id, j.created_at, j.conversion_mode, p.transactions, p.currency, (p.job_id IS NOT NULL) AS has_payload
            FROM jobs j
            LEFT JOIN job_payloads p ON j.id = p.job_id
            WHERE j.user_id = %s
            ORDER BY j.created_at DESC
            LIMIT %s
            """,
            (user_id, limit),
        )
        rows = cur.fetchall()
    out = []
    for row in rows:
        transactions = row["transactions"] if isinstance(row["transactions"], list) else (json.loads(row["transactions"]) if row["transactions"] else [])
        if transactions is None:
            transactions = []
        out.append({
            "id": row["id"],
            "created_at": row["created_at"].isoformat() if hasattr(row["created_at"], "isoformat") else str(row["created_at"]),
            "transaction_count": len(transactions),
            "currency": row["currency"],
            "has_payload": bool(row.get("has_payload")),
            "conversion_mode": row.get("conversion_mode"),
        })
    return out


def get_job(job_id: str, user_id: str) -> dict | None:
    """Return job dict with transactions, csv_content (derived), raw_text, currency, and optional data_status; or None if not found or not owned by user."""
    with _cursor() as cur:
        cur.execute(
            "SELECT id, user_id, created_at, incognito, conversion_mode FROM jobs WHERE id = %s AND user_id = %s",
            (job_id, user_id),
        )
        job_row = cur.fetchone()
    if not job_row:
        return None
    with _cursor() as cur:
        cur.execute(
            "SELECT transactions, raw_text, currency FROM job_payloads WHERE job_id = %s",
            (job_id,),
        )
        payload_row = cur.fetchone()
    if payload_row:
        transactions = payload_row["transactions"] if isinstance(payload_row["transactions"], list) else json.loads(payload_row["transactions"] or "[]")
        csv_content = transactions_to_csv(transactions)
        return {
            "id": job_row["id"],
            "transactions": transactions,
            "csv_content": csv_content,
            "raw_text": payload_row["raw_text"] or "",
            "currency": payload_row["currency"],
            "conversion_mode": job_row.get("conversion_mode"),
        }
    # No payload: incognito or purged
    return {
        "id": job_row["id"],
        "transactions": [],
        "csv_content": "",
        "raw_text": "",
        "currency": None,
        "data_status": "incognito" if job_row["incognito"] else "purged",
        "conversion_mode": job_row.get("conversion_mode"),
    }


def purge_job_data(job_id: str, user_id: str) -> None:
    """Remove payload data for one job. Job row is kept. Idempotent."""
    with _cursor() as cur:
        cur.execute(
            """
            DELETE FROM job_payloads
            WHERE job_id = %s AND job_id IN (SELECT id FROM jobs WHERE user_id = %s)
            """,
            (job_id, user_id),
        )


def purge_jobs_data(job_ids: list[str], user_id: str) -> int:
    """Remove payload data for multiple jobs. Job rows are kept. Returns number of payloads deleted."""
    if not job_ids:
        return 0
    with _cursor() as cur:
        cur.execute(
            """
            DELETE FROM job_payloads
            WHERE job_id = ANY(%s) AND job_id IN (SELECT id FROM jobs WHERE user_id = %s)
            """,
            (job_ids, user_id),
        )
        return cur.rowcount


def delete_user_data(user_id: str) -> None:
    """Delete all jobs (and their payloads via CASCADE) for the given user."""
    with _cursor() as cur:
        cur.execute("DELETE FROM jobs WHERE user_id = %s", (user_id,))


def record_trial_run(job_id: str) -> None:
    """Insert a row into trial_runs for analytics (no PDF/transaction data stored)."""
    with _cursor() as cur:
        cur.execute(
            """
            INSERT INTO trial_runs (job_id, created_at)
            VALUES (%s, NOW())
            """,
            (job_id,),
        )


def update_job_transactions(job_id: str, user_id: str, transactions: list[dict[str, Any]]) -> None:
    """Update stored transactions for a job owned by the user. No-op for incognito/purged jobs (no payload row)."""
    payload_json = json.dumps(transactions)
    with _cursor() as cur:
        cur.execute(
            """
            UPDATE job_payloads
            SET transactions = %s
            WHERE job_id = %s AND job_id IN (SELECT id FROM jobs WHERE user_id = %s)
            """,
            (payload_json, job_id, user_id),
        )


# --- Billing ---

def get_billing(user_id: str) -> dict | None:
    """Return user_billing row or None."""
    with _cursor() as cur:
        cur.execute(
            "SELECT user_id, balance_cents, stripe_customer_id, stripe_subscription_id, created_at, updated_at FROM user_billing WHERE user_id = %s",
            (user_id,),
        )
        row = cur.fetchone()
    if not row:
        return None
    return dict(row)


def get_user_id_by_stripe_customer_id(stripe_customer_id: str) -> str | None:
    """Return user_id for the given Stripe customer id, or None."""
    with _cursor() as cur:
        cur.execute("SELECT user_id FROM user_billing WHERE stripe_customer_id = %s", (stripe_customer_id,))
        row = cur.fetchone()
    return row["user_id"] if row else None


def set_balance(user_id: str, balance_cents: int) -> None:
    """Set balance and updated_at."""
    with _cursor() as cur:
        cur.execute(
            """
            INSERT INTO user_billing (user_id, balance_cents, updated_at)
            VALUES (%s, %s, NOW())
            ON CONFLICT (user_id) DO UPDATE SET balance_cents = EXCLUDED.balance_cents, updated_at = NOW()
            """,
            (user_id, balance_cents),
        )


def add_balance(user_id: str, delta_cents: int) -> None:
    """Add delta to balance (e.g. top-up). Creates row if missing with balance = delta."""
    with _cursor() as cur:
        cur.execute(
            """
            INSERT INTO user_billing (user_id, balance_cents, updated_at)
            VALUES (%s, GREATEST(0, %s), NOW())
            ON CONFLICT (user_id) DO UPDATE SET
              balance_cents = GREATEST(0, user_billing.balance_cents + %s),
              updated_at = NOW()
            """,
            (user_id, delta_cents, delta_cents),
        )


def deduct_balance(user_id: str, amount_cents: float) -> int | None:
    """Deduct amount from balance. Returns new balance_cents or None if insufficient. Uses single UPDATE to avoid races."""
    with _cursor() as cur:
        cur.execute(
            """
            UPDATE user_billing
            SET balance_cents = balance_cents - %s, updated_at = NOW()
            WHERE user_id = %s AND balance_cents >= %s
            RETURNING balance_cents
            """,
            (amount_cents, user_id, amount_cents),
        )
        row = cur.fetchone()
    if row is None:
        return None
    return int(row["balance_cents"])


def set_stripe_ids(user_id: str, stripe_customer_id: str, stripe_subscription_id: str | None = None) -> None:
    """Set or update Stripe customer and optional subscription id."""
    with _cursor() as cur:
        cur.execute(
            """
            INSERT INTO user_billing (user_id, stripe_customer_id, stripe_subscription_id, updated_at)
            VALUES (%s, %s, %s, NOW())
            ON CONFLICT (user_id) DO UPDATE SET
              stripe_customer_id = COALESCE(EXCLUDED.stripe_customer_id, user_billing.stripe_customer_id),
              stripe_subscription_id = COALESCE(EXCLUDED.stripe_subscription_id, user_billing.stripe_subscription_id),
              updated_at = NOW()
            """,
            (user_id, stripe_customer_id, stripe_subscription_id),
        )


def insert_usage_log(user_id: str, job_id: str, amount_cents: float, balance_after_cents: int, conversion_mode: str) -> None:
    """Append a row to billing_usage_log."""
    with _cursor() as cur:
        cur.execute(
            """
            INSERT INTO billing_usage_log (user_id, job_id, amount_cents, balance_after_cents, conversion_mode)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (user_id, job_id, int(amount_cents), balance_after_cents, conversion_mode),
        )
