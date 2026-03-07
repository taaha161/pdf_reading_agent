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
) -> None:
    """Insert or replace job for user. csv_content is derived from transactions when reading; we store transactions, raw_text, currency."""
    with _cursor() as cur:
        cur.execute(
            """
            INSERT INTO jobs (id, user_id, transactions, created_at, raw_text, currency)
            VALUES (%s, %s, %s, NOW(), %s, %s)
            """,
            (job_id, user_id, json.dumps(transactions), raw_text, currency),
        )


def list_jobs(user_id: str, limit: int = 100) -> list[dict]:
    """Return list of jobs for user: id, created_at, transaction_count, currency. Newest first."""
    with _cursor() as cur:
        cur.execute(
            """
            SELECT id, created_at, transactions, currency
            FROM jobs WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (user_id, limit),
        )
        rows = cur.fetchall()
    out = []
    for row in rows:
        transactions = row["transactions"] if isinstance(row["transactions"], list) else json.loads(row["transactions"] or "[]")
        out.append({
            "id": row["id"],
            "created_at": row["created_at"].isoformat() if hasattr(row["created_at"], "isoformat") else str(row["created_at"]),
            "transaction_count": len(transactions),
            "currency": row["currency"],
        })
    return out


def get_job(job_id: str, user_id: str) -> dict | None:
    """Return job dict with transactions, csv_content (derived), raw_text, currency; or None if not found or not owned by user."""
    with _cursor() as cur:
        cur.execute(
            "SELECT id, user_id, transactions, created_at, raw_text, currency FROM jobs WHERE id = %s AND user_id = %s",
            (job_id, user_id),
        )
        row = cur.fetchone()
    if not row:
        return None
    transactions = row["transactions"] if isinstance(row["transactions"], list) else json.loads(row["transactions"] or "[]")
    csv_content = transactions_to_csv(transactions)
    return {
        "id": row["id"],
        "transactions": transactions,
        "csv_content": csv_content,
        "raw_text": row["raw_text"] or "",
        "currency": row["currency"],
    }
