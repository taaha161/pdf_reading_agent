"""Job store: DB-backed (Supabase Postgres). Jobs are scoped by user_id."""
import json
import os
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

from services.csv_export import transactions_to_csv
from services.field_crypto import decrypt_text, encrypt_text


def _parse_amount(amount_str: str) -> float:
    """Parse amount string (may contain commas or leading minus) to float. Returns magnitude."""
    raw = str(amount_str or "0").replace(",", "").strip()
    try:
        return float(raw) if raw else 0.0
    except (ValueError, TypeError):
        return 0.0


def _aggregate_transactions(transactions: list[dict]) -> tuple[float, float, dict[str, float]]:
    """Income (credits with category Income), expenses (debits not Income), category totals (debits only)."""
    total_income = 0.0
    total_expenses = 0.0
    by_category: dict[str, float] = {}
    for t in transactions:
        magnitude = abs(_parse_amount(t.get("amount")))
        is_debit = str(t.get("type", "")).lower() == "debit"
        cat = str(t.get("category", "")).strip() or "Other"
        if cat == "Income":
            if not is_debit:  # credits
                total_income += magnitude
        else:
            if is_debit:
                total_expenses += magnitude
                by_category[cat] = by_category.get(cat, 0) + magnitude
    return total_income, total_expenses, by_category


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
                (job_id, json.dumps(transactions), encrypt_text(raw_text), currency),
            )


def list_jobs(user_id: str, limit: int = 100) -> tuple[list[dict], dict[str, Any] | None]:
    """Return (jobs list, dashboard stats or None). Jobs: id, created_at, transaction_count, currency, etc. Newest first.
    Stats: total_income, total_expenses, surplus, summary_by_category, primary_currency. Computed from same query (no extra DB round-trip)."""
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
    total_income = 0.0
    total_expenses = 0.0
    category_totals: dict[str, float] = {}
    primary_currency: str | None = None
    for row in rows:
        transactions = row["transactions"] if isinstance(row["transactions"], list) else (json.loads(row["transactions"]) if row["transactions"] else [])
        if transactions is None:
            transactions = []
        if row.get("has_payload") and transactions and primary_currency is None:
            primary_currency = row.get("currency")
        inc, exp, by_cat = _aggregate_transactions(transactions)
        total_income += inc
        total_expenses += exp
        for cat, val in by_cat.items():
            category_totals[cat] = category_totals.get(cat, 0) + val
        out.append({
            "id": row["id"],
            "created_at": row["created_at"].isoformat() if hasattr(row["created_at"], "isoformat") else str(row["created_at"]),
            "transaction_count": len(transactions),
            "currency": row["currency"],
            "has_payload": bool(row.get("has_payload")),
            "conversion_mode": row.get("conversion_mode"),
        })
    summary_list = sorted(category_totals.items(), key=lambda x: -x[1])
    stats = {
        "total_income": total_income,
        "total_expenses": total_expenses,
        "surplus": total_income - total_expenses,
        "summary_by_category": [{"category": c, "total": t} for c, t in summary_list],
        "primary_currency": primary_currency,
    }
    return out, stats


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
            "raw_text": decrypt_text(payload_row["raw_text"]) or "",
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
            WHERE job_id = ANY(%s::uuid[]) AND job_id IN (SELECT id FROM jobs WHERE user_id = %s)
            """,
            (job_ids, user_id),
        )
        return cur.rowcount


def delete_user_data(user_id: str) -> None:
    """Delete everything we store under this user id, in one transaction.

    Jobs (payloads cascade), billing balance and usage log, and feedback.
    profiles/subscription cascade when the Supabase auth user is deleted.
    Payment records stay with Stripe.
    """
    with _cursor() as cur:
        cur.execute("DELETE FROM jobs WHERE user_id = %s", (user_id,))
        cur.execute("DELETE FROM billing_usage_log WHERE user_id = %s", (user_id,))
        cur.execute("DELETE FROM user_billing WHERE user_id = %s", (user_id,))
        cur.execute("DELETE FROM scan_feedback WHERE user_id = %s", (user_id,))
        # Commission rows stay (affiliate payout records); the referral link goes.
        cur.execute("DELETE FROM affiliate_referrals WHERE user_id = %s", (user_id,))


def record_trial_run(job_id: str, client_ip_hash: str | None = None, pages: int | None = None) -> None:
    """Insert a row into trial_runs for analytics + durable trial counting.

    ``client_ip_hash`` is a salted one-way hash of the client IP (never the raw
    IP); it lets us count a client's anonymous trial runs server-side so the
    limit survives cookie clearing. No PDF/transaction data is stored.
    """
    with _cursor() as cur:
        cur.execute(
            """
            INSERT INTO trial_runs (job_id, client_ip_hash, pages, created_at)
            VALUES (%s, %s, %s, NOW())
            """,
            (job_id, client_ip_hash, pages),
        )


def count_trial_runs_by_ip(client_ip_hash: str) -> int:
    """Number of anonymous trial runs recorded for this client IP hash."""
    if not client_ip_hash:
        return 0
    with _cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) AS n FROM trial_runs WHERE client_ip_hash = %s",
            (client_ip_hash,),
        )
        row = cur.fetchone()
    return int(row["n"]) if row else 0


def sum_trial_pages_by_ip(client_ip_hash: str) -> int:
    """Free pages this client IP hash has used without an account (runs before page pricing count 0)."""
    if not client_ip_hash:
        return 0
    with _cursor() as cur:
        cur.execute(
            "SELECT COALESCE(SUM(pages), 0) AS n FROM trial_runs WHERE client_ip_hash = %s",
            (client_ip_hash,),
        )
        row = cur.fetchone()
    return int(row["n"]) if row else 0


def trial_run_exists(job_id: str, client_ip_hash: str | None) -> bool:
    """True if this anonymous trial job was run in the last day (by the same client, when hashed)."""
    with _cursor() as cur:
        cur.execute(
            """
            SELECT 1 FROM trial_runs
            WHERE job_id = %s
              AND created_at > NOW() - INTERVAL '1 day'
              AND (%s::text IS NULL OR client_ip_hash IS NULL OR client_ip_hash = %s)
            LIMIT 1
            """,
            (job_id, client_ip_hash, client_ip_hash),
        )
        return cur.fetchone() is not None


def count_email_captures_for_job(job_id: str) -> int:
    with _cursor() as cur:
        cur.execute("SELECT COUNT(*) AS n FROM email_captures WHERE job_id = %s", (job_id,))
        row = cur.fetchone()
    return int(row["n"]) if row else 0


def record_email_capture(
    email: str,
    job_id: str | None,
    marketing_opt_in: bool,
    client_ip_hash: str | None = None,
    source: str = "email_spreadsheet",
) -> None:
    """Store an email captured from an anonymous user (no transaction data)."""
    with _cursor() as cur:
        cur.execute(
            """
            INSERT INTO email_captures (email, source, job_id, marketing_opt_in, client_ip_hash, created_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
            """,
            (email, source, job_id, marketing_opt_in, client_ip_hash),
        )


def record_feedback(
    user_id: str | None,
    job_id: str | None,
    rating: int | None,
    comment: str | None,
    contact_ok: bool,
    client_ip_hash: str | None = None,
) -> None:
    """Store a post-scan feedback response."""
    with _cursor() as cur:
        cur.execute(
            """
            INSERT INTO scan_feedback (user_id, job_id, rating, comment, contact_ok, client_ip_hash, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
            """,
            (user_id, job_id, rating, comment, contact_ok, client_ip_hash),
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
# Pages are the billing unit. A user has three buckets, spent in this order:
#   free_pages (signup grant, expires at free_expires_at) -> plan_pages (monthly
#   subscription allowance, reset each cycle) -> pack_pages (purchased, never expire).

_BILLING_COLS = (
    "user_id, balance_cents, free_pages, free_expires_at, plan_pages, pack_pages, "
    "stripe_customer_id, stripe_subscription_id, created_at, updated_at"
)


def get_billing(user_id: str) -> dict | None:
    """Return user_billing row or None."""
    with _cursor() as cur:
        cur.execute(f"SELECT {_BILLING_COLS} FROM user_billing WHERE user_id = %s", (user_id,))
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


def ensure_free_grant(user_id: str, pages: int, days: int) -> dict:
    """Grant the one-time free pages (valid `days`) if this user never got them. Returns the row."""
    with _cursor() as cur:
        cur.execute(
            f"""
            INSERT INTO user_billing (user_id, free_pages, free_expires_at, updated_at)
            VALUES (%s, %s, NOW() + make_interval(days => %s), NOW())
            ON CONFLICT (user_id) DO UPDATE SET
              free_pages = EXCLUDED.free_pages,
              free_expires_at = EXCLUDED.free_expires_at,
              updated_at = NOW()
            WHERE user_billing.free_expires_at IS NULL
            RETURNING {_BILLING_COLS}
            """,
            (user_id, pages, days),
        )
        row = cur.fetchone()
        if row is None:
            cur.execute(f"SELECT {_BILLING_COLS} FROM user_billing WHERE user_id = %s", (user_id,))
            row = cur.fetchone()
    return dict(row)


def free_pages_available(row: dict | None, now: datetime | None = None) -> int:
    """Unexpired free pages on a billing row."""
    if not row or not row.get("free_expires_at"):
        return 0
    now = now or datetime.now(timezone.utc)
    return max(0, int(row.get("free_pages") or 0)) if row["free_expires_at"] > now else 0


def pages_available(row: dict | None) -> int:
    """Total pages this user can spend right now."""
    if not row:
        return 0
    return free_pages_available(row) + max(0, int(row.get("plan_pages") or 0)) + max(0, int(row.get("pack_pages") or 0))


def set_plan_pages(user_id: str, pages: int) -> None:
    """Set the monthly plan allowance (subscription start / renewal / cancel)."""
    with _cursor() as cur:
        cur.execute(
            """
            INSERT INTO user_billing (user_id, plan_pages, updated_at)
            VALUES (%s, %s, NOW())
            ON CONFLICT (user_id) DO UPDATE SET plan_pages = EXCLUDED.plan_pages, updated_at = NOW()
            """,
            (user_id, pages),
        )


def add_pack_pages(user_id: str, pages: int) -> None:
    """Add purchased pages (never expire)."""
    with _cursor() as cur:
        cur.execute(
            """
            INSERT INTO user_billing (user_id, pack_pages, updated_at)
            VALUES (%s, GREATEST(0, %s), NOW())
            ON CONFLICT (user_id) DO UPDATE SET
              pack_pages = GREATEST(0, user_billing.pack_pages + %s),
              updated_at = NOW()
            """,
            (user_id, pages, pages),
        )


def deduct_pages(user_id: str, pages: int) -> dict | None:
    """Spend `pages` (free -> plan -> pack), atomically. Returns the updated row, or None if not enough."""
    with _cursor() as cur:
        cur.execute(f"SELECT {_BILLING_COLS} FROM user_billing WHERE user_id = %s FOR UPDATE", (user_id,))
        row = cur.fetchone()
        if row is None or pages_available(row) < pages:
            return None
        row = dict(row)
        left = pages
        take_free = min(left, free_pages_available(row))
        left -= take_free
        take_plan = min(left, max(0, row["plan_pages"]))
        left -= take_plan
        take_pack = left
        cur.execute(
            f"""
            UPDATE user_billing SET
              free_pages = free_pages - %s,
              plan_pages = plan_pages - %s,
              pack_pages = pack_pages - %s,
              updated_at = NOW()
            WHERE user_id = %s
            RETURNING {_BILLING_COLS}
            """,
            (take_free, take_plan, take_pack, user_id),
        )
        return dict(cur.fetchone())


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


def insert_usage_log(user_id: str, job_id: str, pages: int, pages_after: int, conversion_mode: str) -> None:
    """Append a row to billing_usage_log (pages charged; balance_after_cents holds pages left)."""
    with _cursor() as cur:
        cur.execute(
            """
            INSERT INTO billing_usage_log (user_id, job_id, amount_cents, balance_after_cents, conversion_mode, pages)
            VALUES (%s, %s, 0, %s, %s, %s)
            """,
            (user_id, job_id, pages_after, conversion_mode, pages),
        )


# --- Affiliates ---

_AFFILIATE_COLS = (
    "id, name, email, code, revenue_share_pct, commission_months, discount_pct, discount_months, "
    "discount_packs, stripe_coupon_id, active, notes, created_at, updated_at"
)


def create_affiliate(
    name: str,
    code: str,
    revenue_share_pct: float,
    email: str | None = None,
    commission_months: int | None = None,
    notes: str | None = None,
    discount_pct: float = 0,
    discount_months: int | None = None,
    discount_packs: bool = False,
) -> dict:
    """Insert an affiliate. Raises psycopg2.errors.UniqueViolation if the code is taken."""
    with _cursor() as cur:
        cur.execute(
            f"""
            INSERT INTO affiliates
              (name, email, code, revenue_share_pct, commission_months, notes, discount_pct, discount_months, discount_packs)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING {_AFFILIATE_COLS}
            """,
            (name, email, code, revenue_share_pct, commission_months, notes, discount_pct, discount_months, discount_packs),
        )
        return dict(cur.fetchone())


_AFFILIATE_UPDATABLE = (
    "name", "email", "revenue_share_pct", "commission_months", "active", "notes",
    "discount_pct", "discount_months", "discount_packs",
)


def update_affiliate(affiliate_id: str, fields: dict) -> dict | None:
    """Update the given fields (subset of _AFFILIATE_UPDATABLE). Returns the row or None if missing.

    Changing the discount clears stripe_coupon_id (Stripe coupons are immutable), so
    the next checkout creates a coupon with the new terms. Existing subscriptions keep theirs.
    """
    fields = {k: v for k, v in fields.items() if k in _AFFILIATE_UPDATABLE}
    with _cursor() as cur:
        if fields:
            sets = ", ".join(f"{k} = %s" for k in fields)
            if {"discount_pct", "discount_months"} & fields.keys():
                sets += ", stripe_coupon_id = NULL"
            cur.execute(
                f"UPDATE affiliates SET {sets}, updated_at = NOW() WHERE id = %s RETURNING {_AFFILIATE_COLS}",
                (*fields.values(), affiliate_id),
            )
        else:
            cur.execute(f"SELECT {_AFFILIATE_COLS} FROM affiliates WHERE id = %s", (affiliate_id,))
        row = cur.fetchone()
    return dict(row) if row else None


def set_affiliate_coupon(affiliate_id: str, coupon_id: str) -> None:
    with _cursor() as cur:
        cur.execute("UPDATE affiliates SET stripe_coupon_id = %s WHERE id = %s", (coupon_id, affiliate_id))


def get_affiliate_by_code(code: str) -> dict | None:
    with _cursor() as cur:
        cur.execute(f"SELECT {_AFFILIATE_COLS} FROM affiliates WHERE code = %s", (code,))
        row = cur.fetchone()
    return dict(row) if row else None


def list_affiliates() -> list[dict]:
    """All affiliates with referral count and commission totals (cents)."""
    with _cursor() as cur:
        cur.execute(
            f"""
            SELECT {", ".join("a." + c.strip() for c in _AFFILIATE_COLS.split(","))},
              (SELECT COUNT(*) FROM affiliate_referrals r WHERE r.affiliate_id = a.id) AS referrals,
              COALESCE(SUM(c.amount_cents) FILTER (WHERE c.status <> 'void'), 0) AS revenue_cents,
              COALESCE(SUM(c.commission_cents) FILTER (WHERE c.status = 'pending'), 0) AS pending_cents,
              COALESCE(SUM(c.commission_cents) FILTER (WHERE c.status = 'paid'), 0) AS paid_cents
            FROM affiliates a
            LEFT JOIN affiliate_commissions c ON c.affiliate_id = a.id
            GROUP BY a.id
            ORDER BY a.created_at DESC
            """
        )
        return [dict(r) for r in cur.fetchall()]


def get_auth_user(user_id: str | None = None, email: str | None = None) -> dict | None:
    """Supabase auth user by id or (case-insensitive) email.

    {id, email, created_at, has_password, paid_signup_customer, full_name}:
    paid_signup_customer is the Stripe customer whose guest checkout created this
    account (paid signup), else None; full_name is the display name, else None.
    """
    if not user_id and not email:
        return None
    where, arg = ("id::text = %s", user_id) if user_id else ("lower(email) = lower(%s)", email)
    with _cursor() as cur:
        cur.execute(
            f"""
            SELECT id::text AS id, email, created_at,
                   (coalesce(encrypted_password, '') <> '') AS has_password,
                   raw_user_meta_data->>'paid_signup_customer' AS paid_signup_customer,
                   coalesce(nullif(trim(raw_user_meta_data->>'full_name'), ''),
                            nullif(trim(raw_user_meta_data->>'name'), '')) AS full_name
            FROM auth.users WHERE {where} AND deleted_at IS NULL
            ORDER BY created_at LIMIT 1
            """,
            (arg,),
        )
        row = cur.fetchone()
    return dict(row) if row else None


def mark_free_grant_used(user_id: str) -> None:
    """Paid signups skip the free month: record the one-time grant as already spent.

    ensure_free_grant only grants while free_expires_at IS NULL, so setting it
    (with 0 pages) means the grant never happens for this account.
    """
    with _cursor() as cur:
        cur.execute(
            """
            INSERT INTO user_billing (user_id, free_pages, free_expires_at, updated_at)
            VALUES (%s, 0, NOW(), NOW())
            ON CONFLICT (user_id) DO UPDATE SET
              free_expires_at = COALESCE(user_billing.free_expires_at, NOW()),
              updated_at = NOW()
            """,
            (user_id,),
        )


def get_user_created_at(user_id: str) -> datetime | None:
    """Supabase auth account creation time (backend connects as owner, so auth.users is readable)."""
    with _cursor() as cur:
        cur.execute("SELECT created_at FROM auth.users WHERE id::text = %s", (user_id,))
        row = cur.fetchone()
    return row["created_at"] if row else None


def create_referral(user_id: str, affiliate_id: str, code: str) -> bool:
    """Bind user to affiliate. First binding wins; returns False if the user already had one."""
    with _cursor() as cur:
        cur.execute(
            """
            INSERT INTO affiliate_referrals (user_id, affiliate_id, code)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id) DO NOTHING
            """,
            (user_id, affiliate_id, code),
        )
        return cur.rowcount == 1


def get_referral_with_affiliate(user_id: str) -> dict | None:
    """The user's referral joined with its affiliate's current terms, or None."""
    with _cursor() as cur:
        cur.execute(
            """
            SELECT r.user_id, r.affiliate_id, r.code, r.created_at AS referred_at,
                   a.revenue_share_pct, a.commission_months, a.active,
                   a.discount_pct, a.discount_months, a.discount_packs, a.stripe_coupon_id
            FROM affiliate_referrals r JOIN affiliates a ON a.id = r.affiliate_id
            WHERE r.user_id = %s
            """,
            (user_id,),
        )
        row = cur.fetchone()
    return dict(row) if row else None


def insert_commission(
    affiliate_id: str,
    user_id: str,
    source_id: str,
    kind: str,
    amount_cents: int,
    currency: str,
    revenue_share_pct,
    commission_cents: int,
) -> bool:
    """Record one commission. Idempotent on source_id; returns False if already recorded."""
    with _cursor() as cur:
        cur.execute(
            """
            INSERT INTO affiliate_commissions
              (affiliate_id, user_id, source_id, kind, amount_cents, currency, revenue_share_pct, commission_cents)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (source_id) DO NOTHING
            """,
            (affiliate_id, user_id, source_id, kind, amount_cents, currency, revenue_share_pct, commission_cents),
        )
        return cur.rowcount == 1


def list_commissions(affiliate_id: str, status: str | None = None, limit: int = 500) -> list[dict]:
    with _cursor() as cur:
        cur.execute(
            """
            SELECT id, user_id, source_id, kind, amount_cents, currency, revenue_share_pct,
                   commission_cents, status, paid_at, created_at
            FROM affiliate_commissions
            WHERE affiliate_id = %s AND (%s::text IS NULL OR status = %s)
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (affiliate_id, status, status, limit),
        )
        return [dict(r) for r in cur.fetchall()]


def mark_commissions_paid(affiliate_id: str, before: datetime | None = None) -> dict:
    """Mark pending commissions (created before `before`, default now) as paid. Returns count and total."""
    with _cursor() as cur:
        cur.execute(
            """
            UPDATE affiliate_commissions SET status = 'paid', paid_at = NOW()
            WHERE affiliate_id = %s AND status = 'pending' AND created_at <= COALESCE(%s, NOW())
            RETURNING commission_cents
            """,
            (affiliate_id, before),
        )
        rows = cur.fetchall()
    return {"count": len(rows), "total_cents": sum(r["commission_cents"] for r in rows)}
