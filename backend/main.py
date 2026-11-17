import csv
import hashlib
import hmac
import io
import logging
import os
import re
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

_LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").strip().upper()
logging.basicConfig(
    level=getattr(logging, _LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("pdf_processor_app")

from services.monitoring import UNCAUGHT_LOGGER, capture_message as capture_monitoring_message, init_monitoring

init_monitoring()  # before FastAPI is imported/created so its integration hooks in

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from auth import get_current_claims, get_current_user, get_current_user_optional
from models.schemas import (
    AffiliateCreateRequest,
    AffiliatePayoutRequest,
    AffiliateUpdateRequest,
    ReferralClaimRequest,
    BillingBalanceResponse,
    UsageResponse,
    CategorySummary,
    ChatRequest,
    ChatResponse,
    CheckoutSessionRequest,
    CheckoutSessionResponse,
    GuestCheckoutRequest,
    PaidSignupPasswordRequest,
    DashboardStats,
    EmailSpreadsheetRequest,
    ExportRequest,
    FeedbackRequest,
    FetchPdfUrlRequest,
    JobDetailResponse,
    JobListItem,
    JobListResponse,
    ProcessPdfResponse,
    PurgeJobsDataRequest,
    Transaction,
    UpdateJobTransactionsRequest,
)
from services.billing import (
    FREE_ANON_PAGES,
    FREE_SIGNUP_DAYS,
    FREE_SIGNUP_PAGES,
    create_checkout_session,
    handle_webhook,
    scan_cost_pages,
)
from services.affiliates import claim_referral, normalize_code, public_discount, user_discount, valid_code
from services import paid_signup
from services.chat_service import get_reply
from services.summary import _parse_amount, _summary_by_category  # noqa: F401
from services.remote_pdf import RemotePdfError, RemotePdfTooLarge, fetch_pdf
from services.csv_export import summary_to_csv, transactions_to_csv
from services.xlsx_export import XLSX_MIME, summary_to_xlsx, transactions_to_xlsx
from services.notifications import (
    notify_email_capture,
    notify_feedback,
    name_from_metadata,
    notify_login,
    notify_scan,
    notify_signup,
    send_spreadsheet_email,
)
from services.pdf_processor import (
    PdfExtractionTimeout,
    PdfPasswordRequired,
    MAX_PDF_PAGES,
    PdfTooManyPages,
    count_pdf_pages,
    decrypt_pdf,
    extract_text_from_pdf,
)
from services.scan_jobs import create_scan, fail_scan, finish_scan, get_scan, set_stage as set_scan_stage
from services.recaptcha import verify_recaptcha
from services.statement_agent import extract_and_categorize
from store import (
    get_auth_user,
    get_job_owner,
    create_job_id,
    deduct_pages,
    delete_user_data,
    ensure_free_grant,
    free_pages_available,
    get_billing,
    get_referral_with_affiliate,
    pages_available,
    get_job,
    insert_usage_log,
    list_jobs,
    purge_job_data,
    purge_jobs_data,
    record_trial_run,
    sum_trial_pages_by_ip,
    count_email_captures_for_job,
    record_email_capture,
    record_feedback,
    trial_run_exists,
    set_job,
    update_job_transactions,
)
import store

try:
    import psycopg2
    import psycopg2.errors
except ImportError:
    psycopg2 = None

# Header carrying the real client IP. Render sits behind Cloudflare, which sets
# CF-Connecting-IP and overwrites any client-supplied value. The left-most
# X-Forwarded-For entry is client-controlled, so it is only a last resort.
_CLIENT_IP_HEADER = os.environ.get("CLIENT_IP_HEADER", "cf-connecting-ip").strip().lower()

_TRIAL_IP_SALT = os.environ.get("TRIAL_IP_SALT", "").strip()
if not _TRIAL_IP_SALT:
    logger.warning("TRIAL_IP_SALT not set — using an insecure default salt for IP hashing")
    _TRIAL_IP_SALT = "bss-default-trial-salt"


def _client_ip(request: Request) -> str | None:
    """Best-effort real client IP behind Cloudflare/Render."""
    ip = request.headers.get(_CLIENT_IP_HEADER, "").strip()
    if ip:
        return ip
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        return xff.split(",")[0].strip() or None
    client = getattr(request, "client", None)
    return getattr(client, "host", None) if client else None


def _client_ip_hash(request: Request) -> str | None:
    """Salted one-way hash of the client IP for durable trial counting (never stores the raw IP)."""
    ip = _client_ip(request)
    if not ip:
        return None
    return hmac.new(_TRIAL_IP_SALT.encode(), ip.encode(), hashlib.sha256).hexdigest()


_REDIS_URL = os.environ.get("REDIS_URL", "").strip()
# Key rate limits on the real client IP, not the proxy's address.
_limiter_kwargs = {"key_func": lambda request: _client_ip(request) or "unknown"}
if _REDIS_URL:
    _limiter_kwargs["storage_uri"] = _REDIS_URL
limiter = Limiter(**_limiter_kwargs)

app = FastAPI(title="PDF Bank Statement Processor")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

GENERIC_500_MESSAGE = "Something went wrong. Please try again later."


@app.exception_handler(Exception)
def _handle_uncaught_exception(request: Request, exc: Exception):
    """Return generic 500 for uncaught errors; preserve HTTPException status and detail (generic detail for 500)."""
    from fastapi import HTTPException as HTTPEx
    if isinstance(exc, HTTPEx):
        detail = GENERIC_500_MESSAGE if exc.status_code == 500 else exc.detail
        return JSONResponse(status_code=exc.status_code, content={"detail": detail})
    # Own logger: Sentry's FastAPI integration already reports this exception, so
    # monitoring ignores this logger (UNCAUGHT_LOGGER) to avoid a duplicate event.
    logging.getLogger(UNCAUGHT_LOGGER).error("Uncaught exception: %s", exc, exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": GENERIC_500_MESSAGE})


if psycopg2 is not None:
    @app.exception_handler(psycopg2.OperationalError)
    def _handle_db_unavailable(request, exc):
        """Return 503 when database is unreachable (e.g. DNS/network)."""
        return JSONResponse(
            status_code=503,
        content={"detail": "Database unavailable. Please try again later."},
        )

# CORS: allow origins from ALLOWED_ORIGINS (comma-separated); if unset, use defaults. Localhost and production are always allowed.
_VERCEL_ORIGIN = "https://bankstatementscanner.com"
_EXTRA_ORIGINS = (
    "https://pdftoexcelconverter.io",
    "https://pdf-reading-agent.vercel.app",
)
_LOCALHOST_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
)
_origins_raw = os.environ.get("ALLOWED_ORIGINS", "").strip()
if _origins_raw:
    _origins_list = [o.strip().rstrip("/") for o in _origins_raw.split(",") if o.strip()]
else:
    _origins_list = []
# Always merge localhost and production origins so CORS works in dev and prod
for _origin in _LOCALHOST_ORIGINS + (_VERCEL_ORIGIN,) + _EXTRA_ORIGINS:
    if _origin not in _origins_list:
        _origins_list.append(_origin)


def _is_allowed_origin(origin: str) -> bool:
    if not origin or not origin.strip():
        return False
    origin = origin.strip()
    return origin in _origins_list
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Requested-With", "Origin"],
    expose_headers=["*"],
)


# When credentials=true, browsers require explicit header names (not *).
_CORS_ALLOW_HEADERS = "Authorization, Content-Type, Accept, X-Requested-With, Origin"

def _cors_headers(origin: str) -> dict:
    """CORS headers to attach when origin is allowed."""
    return {
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, HEAD, OPTIONS, PATCH",
        "Access-Control-Allow-Headers": _CORS_ALLOW_HEADERS,
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Max-Age": "86400",
    }


class PreflightMiddleware(BaseHTTPMiddleware):
    """Handle all OPTIONS (preflight) with 200 + CORS for allowed origins."""

    async def dispatch(self, request: Request, call_next):
        if request.method != "OPTIONS":
            return await call_next(request)
        origin = request.headers.get("origin", "").strip()
        if _is_allowed_origin(origin):
            return Response(status_code=200, headers=_cors_headers(origin))
        return Response(status_code=204)


class AddCorsToResponseMiddleware(BaseHTTPMiddleware):
    """Add CORS headers to every response when request Origin is allowed."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        origin = request.headers.get("origin", "").strip()
        if _is_allowed_origin(origin):
            for key, value in _cors_headers(origin).items():
                response.headers[key] = value
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses. HSTS only when PRODUCTION=1 or request is HTTPS."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        is_https = getattr(request.url, "scheme", "") == "https"
        if os.environ.get("PRODUCTION", "").strip().lower() in ("1", "true", "yes") or is_https:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        return response


app.add_middleware(PreflightMiddleware)
app.add_middleware(AddCorsToResponseMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

_MB = 1024 * 1024
# Upload size limit by tier. Mirrored client-side via /api/usage max_file_bytes.
MAX_FILE_SIZE = 20 * _MB  # anonymous
MAX_FILE_SIZE_SIGNED_IN = 30 * _MB  # free account
MAX_FILE_SIZE_PAID = 50 * _MB  # active subscription
FILE_TOO_LARGE_CODE = "FILE_TOO_LARGE"
ALLOWED_CONTENT_TYPE = "application/pdf"


@app.get("/health")
def health():
    out = {"status": "ok"}
    api_key = os.environ.get("DATALAB_API_KEY", "").strip()
    if api_key:
        base = os.environ.get("DATALAB_BASE_URL", "https://www.datalab.to").rstrip("/")
        try:
            import httpx
            r = httpx.get(f"{base}/api/v1/health", headers={"X-API-Key": api_key}, timeout=5.0)
            out["datalab"] = "ok" if r.status_code == 200 and (r.json() or {}).get("status") == "ok" else "error"
        except Exception:
            out["datalab"] = "error"
    return out


async def _preflight_response(request: Request):
    origin = request.headers.get("origin", "")
    if origin and origin in _origins_list:
        return Response(status_code=200, headers=_cors_headers(origin))
    return Response(status_code=204)


@app.options("/api/process-pdf")
async def preflight_process_pdf(request: Request):
    return await _preflight_response(request)


@app.options("/api/chat")
async def preflight_chat(request: Request):
    return await _preflight_response(request)


@app.options("/api/jobs")
async def preflight_jobs_list(request: Request):
    return await _preflight_response(request)


@app.options("/api/jobs/{job_id}")
async def preflight_job_detail(request: Request, job_id: uuid.UUID):
    return await _preflight_response(request)


@app.options("/api/jobs/{job_id}/csv")
async def preflight_csv(request: Request, job_id: uuid.UUID):
    return await _preflight_response(request)


@app.options("/api/jobs/{job_id}/markdown")
async def preflight_markdown(request: Request, job_id: uuid.UUID):
    return await _preflight_response(request)


@app.options("/api/jobs/{job_id}/data")
async def preflight_job_data(request: Request, job_id: uuid.UUID):
    return await _preflight_response(request)


@app.options("/api/jobs/data")
async def preflight_jobs_data(request: Request):
    return await _preflight_response(request)


@app.options("/api/account")
async def preflight_account(request: Request):
    return await _preflight_response(request)


@app.options("/api/email-spreadsheet")
async def preflight_email_spreadsheet(request: Request):
    return await _preflight_response(request)


@app.options("/api/export")
async def preflight_export(request: Request):
    return await _preflight_response(request)


@app.delete("/api/account")
async def delete_account(user_id: str = Depends(get_current_user)):
    """Delete current user's app data and Supabase Auth user. Requires SUPABASE_SERVICE_ROLE_KEY."""
    supabase_url = (os.environ.get("SUPABASE_URL", "").strip()).rstrip("/")
    service_role_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not supabase_url or not service_role_key:
        raise HTTPException(
            503,
            "Account deletion is not configured. Please contact support.",
        )
    delete_user_data(user_id)
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            r = await client.delete(
                f"{supabase_url}/auth/v1/admin/users/{user_id}",
                headers={
                    "Authorization": f"Bearer {service_role_key}",
                    "apikey": service_role_key,
                },
                timeout=10.0,
            )
        if r.status_code >= 400:
            logger.warning("Supabase admin delete user failed: status=%s body=%s", r.status_code, r.text)
            raise HTTPException(502, "Could not complete account deletion. Please try again or contact support.")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Supabase admin delete user error: %s", e)
        raise HTTPException(502, "Could not complete account deletion. Please try again or contact support.")
    return Response(status_code=204)


@app.get("/api/jobs", response_model=JobListResponse)
def list_user_jobs(user_id: str = Depends(get_current_user)):
    """List current user's jobs (newest first) and dashboard stats (income, expenses, surplus, category breakdown)."""
    jobs, stats = list_jobs(user_id)
    stats_model = DashboardStats(**stats) if stats else None
    return JobListResponse(jobs=[JobListItem(**j) for j in jobs], stats=stats_model)


@app.get("/api/jobs/{job_id}", response_model=JobDetailResponse)
def get_job_detail(job_id: uuid.UUID, user_id: str = Depends(get_current_user)):
    """Get one job's data for viewing (transactions + summary)."""
    job = get_job(str(job_id), user_id)
    if not job:
        raise HTTPException(404, "Job not found")
    summary = _summary_by_category(job["transactions"])
    return JobDetailResponse(
        job_id=str(job_id),
        transactions=[Transaction(**t) for t in job["transactions"]],
        summary_by_category=[CategorySummary(category=c, total=t) for c, t in summary],
        currency=job.get("currency"),
        data_status=job.get("data_status"),
        conversion_mode=job.get("conversion_mode"),
    )


@app.patch("/api/jobs/{job_id}", response_model=JobDetailResponse)
def update_job_detail(
    job_id: uuid.UUID,
    body: UpdateJobTransactionsRequest,
    user_id: str = Depends(get_current_user),
):
    """Update transactions for a job and return refreshed detail (including summary)."""
    job = get_job(str(job_id), user_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job.get("data_status"):
        # Incognito or purged job: no payload to update
        raise HTTPException(404, "No data for this job")

    update_job_transactions(str(job_id), user_id, [t.model_dump(mode="json") for t in body.transactions])

    updated = get_job(str(job_id), user_id)
    summary = _summary_by_category(updated["transactions"])
    return JobDetailResponse(
        job_id=str(job_id),
        transactions=[Transaction(**t) for t in updated["transactions"]],
        summary_by_category=[CategorySummary(category=c, total=t) for c, t in summary],
        currency=updated.get("currency"),
        data_status=updated.get("data_status"),
        conversion_mode=updated.get("conversion_mode"),
    )


_RATE_LIMIT_PROCESS_PDF = os.environ.get("RATE_LIMIT_PROCESS_PDF", "10/minute")
_RATE_LIMIT_CHAT = os.environ.get("RATE_LIMIT_CHAT", "30/minute")
_RATE_LIMIT_EMAIL_SPREADSHEET = os.environ.get("RATE_LIMIT_EMAIL_SPREADSHEET", "5/hour")
_RATE_LIMIT_EXPORT = os.environ.get("RATE_LIMIT_EXPORT", "30/minute")
_RATE_LIMIT_FEEDBACK = os.environ.get("RATE_LIMIT_FEEDBACK", "10/hour")
_RATE_LIMIT_FETCH_URL = os.environ.get("RATE_LIMIT_FETCH_URL", "10/minute")
_RATE_LIMIT_SCAN_STATUS = os.environ.get("RATE_LIMIT_SCAN_STATUS", "120/minute")


TRIAL_LIMIT_MESSAGE = (
    f"Trial limit reached. You've used your {FREE_ANON_PAGES} free pages. "
    f"Create a free account to get {FREE_SIGNUP_PAGES} free pages for your first month."
)
FREE_PAGES_EXCEEDED_CODE = "FREE_PAGES_EXCEEDED"
TRIAL_LIMIT_CODE = "TRIAL_LIMIT"
INSUFFICIENT_CREDITS_CODE = "INSUFFICIENT_CREDITS"


def _subscription_active(billing: dict | None) -> bool:
    return bool(billing and billing.get("stripe_subscription_id"))


_UNLOADED = object()


def _max_file_size(user_id: str | None, billing=_UNLOADED) -> int:
    """Upload limit for this caller: anonymous < signed in < subscribed.
    Pass `billing` (row or None) if already loaded to skip the lookup."""
    if user_id is None:
        return MAX_FILE_SIZE
    if billing is _UNLOADED:
        billing = get_billing(user_id)
    return MAX_FILE_SIZE_PAID if _subscription_active(billing) else MAX_FILE_SIZE_SIGNED_IN


def _file_too_large(size_bytes: int, max_bytes: int, user_id: str | None, source: str, filename: str = "") -> HTTPException:
    """Log the rejection (with size, so it can be investigated) and build the 413 the client understands.
    `upgrade` tells the client what raises the limit: "signup", "subscribe", or None (already at max)."""
    tier = "anonymous" if user_id is None else ("paid" if max_bytes >= MAX_FILE_SIZE_PAID else "free")
    logger.warning(
        "%s: rejected, file too large: filename=%s, size=%d bytes (%.1f MB), limit=%d MB, tier=%s",
        source, filename, size_bytes, size_bytes / _MB, max_bytes // _MB, tier,
    )
    if user_id is None:
        upgrade, hint = "signup", f" Create a free account to upload up to {MAX_FILE_SIZE_SIGNED_IN // _MB} MB."
    elif max_bytes < MAX_FILE_SIZE_PAID:
        upgrade, hint = "subscribe", f" Subscribe to upload up to {MAX_FILE_SIZE_PAID // _MB} MB."
    else:
        upgrade, hint = None, " Try splitting it into smaller PDFs."
    return HTTPException(
        status_code=413,
        detail={
            "detail": f"This PDF is {size_bytes / _MB:.1f} MB. The maximum file size is {max_bytes // _MB} MB.{hint}",
            "code": FILE_TOO_LARGE_CODE,
            "size_bytes": size_bytes,
            "max_bytes": max_bytes,
            "upgrade": upgrade,
        },
    )
RECAPTCHA_FAILED_CODE = "RECAPTCHA_FAILED"


PDF_PASSWORD_REQUIRED_CODE = "PDF_PASSWORD_REQUIRED"


def _anon_pages_used(request: Request) -> int:
    """Free pages this client has used without an account, counted server-side per IP
    (no cookies, so clearing cookies / incognito can't reset the limit).

    Fails closed: if the count can't be read, treat the free pages as used up.
    """
    ip_hash = _client_ip_hash(request)
    if not ip_hash:
        logger.warning("trial: no client IP; treating free pages as used up")
        return FREE_ANON_PAGES
    try:
        return min(sum_trial_pages_by_ip(ip_hash), FREE_ANON_PAGES)
    except Exception as e:
        logger.error("trial IP page count failed; treating free pages as used up: %s", e)
        return FREE_ANON_PAGES


def _load_billing(user_id: str) -> dict:
    """Billing row for a signed-in user, granting the one-time free month on first sight."""
    return ensure_free_grant(user_id, FREE_SIGNUP_PAGES, FREE_SIGNUP_DAYS)


def _billing_fields(billing: dict | None) -> dict:
    """Page balance fields shared by /api/usage, /api/billing/balance and scan responses."""
    if not billing:
        return {"pages_remaining": 0, "free_pages": 0, "free_expires_at": None, "plan_pages": 0, "pack_pages": 0}
    free = free_pages_available(billing)
    return {
        "pages_remaining": pages_available(billing),
        "free_pages": free,
        "free_expires_at": billing.get("free_expires_at") if free else None,
        "plan_pages": max(0, int(billing.get("plan_pages") or 0)),
        "pack_pages": max(0, int(billing.get("pack_pages") or 0)),
    }


def _insufficient_pages(required: int, remaining: int) -> HTTPException:
    return HTTPException(
        status_code=402,
        detail={
            "detail": (
                f"This scan needs {required:,} page{'s' if required != 1 else ''} and you have "
                f"{remaining:,} left. Subscribe or add a page pack to continue."
            ),
            "code": INSUFFICIENT_CREDITS_CODE,
            "pages_required": required,
            "pages_remaining": remaining,
        },
    )


@app.options("/api/fetch-pdf-url")
async def preflight_fetch_pdf_url(request: Request):
    return await _preflight_response(request)


@app.post("/api/fetch-pdf-url")
@limiter.limit(_RATE_LIMIT_FETCH_URL)
async def fetch_pdf_url(
    request: Request,
    body: FetchPdfUrlRequest,
    user_id: str | None = Depends(get_current_user_optional),
):
    """Download a PDF from a public link (direct URL, Google Drive/Dropbox share link) and
    return its bytes. The client then submits it to /api/process-pdf like a local file,
    so reCAPTCHA, trial and credit checks all still apply there."""
    try:
        content, filename = await fetch_pdf(body.url, _max_file_size(user_id))
    except RemotePdfTooLarge as e:
        raise _file_too_large(e.size_bytes, e.max_bytes, user_id, "fetch-pdf-url", body.url[:200])
    except RemotePdfError as e:
        raise HTTPException(status_code=400, detail=str(e))
    logger.info("fetch-pdf-url: downloaded %d bytes", len(content))
    return Response(
        content=content,
        media_type=ALLOWED_CONTENT_TYPE,
        headers={"X-Filename": filename, "Access-Control-Expose-Headers": "X-Filename"},
    )


@dataclass
class _ScanRequest:
    """A validated scan, ready to run: checks passed and the PDF already decrypted."""

    content: bytes
    filename: str
    user_id: str | None
    page_count: int
    cost_pages: int
    anon_pages_used: int  # anonymous only: free pages used before this scan
    scanned_method: str
    conversion_mode: str
    incognito: bool
    ip_hash: str | None


ProgressFn = Callable[..., None]


def _no_progress(*_args, **_kwargs) -> None:
    pass


async def _prepare_scan(
    request: Request,
    file: UploadFile,
    scanned_method: str,
    incognito_mode: str,
    conversion_mode: str,
    pdf_password: str | None,
    recaptcha_token: str | None,
    user_id: str | None,
) -> _ScanRequest:
    """Fast checks that must fail before a scan starts: bot check, trial/credits,
    file validation and PDF decryption (so password errors return immediately)."""
    # Bot check before any (paid) processing, for every scan — anonymous or not.
    if not await verify_recaptcha(recaptcha_token, _client_ip(request)):
        raise HTTPException(
            status_code=403,
            detail={"detail": "reCAPTCHA verification failed. Please refresh and try again.", "code": RECAPTCHA_FAILED_CODE},
        )

    # Anonymous free pages are counted server-side per client IP.
    anon_used = 0
    if user_id is None:
        anon_used = _anon_pages_used(request)
        if anon_used >= FREE_ANON_PAGES:
            raise HTTPException(status_code=401, detail={"detail": TRIAL_LIMIT_MESSAGE, "code": TRIAL_LIMIT_CODE})

    # Normalize: only "ocr" or "vision" (for scanned PDFs)
    scanned_method_val = "ocr" if scanned_method and scanned_method.strip().lower() == "ocr" else "vision"
    # Datalab processing mode: fast | balanced | accurate
    conversion_mode_val = (conversion_mode or "fast").strip().lower()
    if conversion_mode_val not in ("fast", "balanced", "accurate"):
        conversion_mode_val = "fast"
    logger.info("scan: request started, scanned_method=%s, conversion_mode=%s", scanned_method_val, conversion_mode_val)

    billing = _load_billing(user_id) if user_id is not None else None
    # Out of pages entirely: fail before reading the upload.
    if billing is not None and pages_available(billing) <= 0:
        raise _insufficient_pages(scan_cost_pages(1, conversion_mode_val), 0)

    if file.content_type and file.content_type != ALLOWED_CONTENT_TYPE:
        raise HTTPException(400, "File must be a PDF")
    max_bytes = _max_file_size(user_id, billing)
    if file.size is not None and file.size > max_bytes:
        raise _file_too_large(file.size, max_bytes, user_id, "scan", file.filename or "")
    content = await file.read()
    if len(content) > max_bytes:
        raise _file_too_large(len(content), max_bytes, user_id, "scan", file.filename or "")
    if not content:
        raise HTTPException(400, "Empty file")

    try:
        content = await run_in_threadpool(decrypt_pdf, content, (pdf_password or "").strip() or None)
    except Exception as e:
        raise _pdf_error(e)

    # Count pages before any processing: this is what the scan costs.
    page_count = await run_in_threadpool(count_pdf_pages, content)
    if page_count <= 0:
        raise HTTPException(422, "We couldn't read this PDF. Make sure it's a valid bank statement and try again.")
    if page_count > MAX_PDF_PAGES:
        raise _pdf_error(PdfTooManyPages(page_count, MAX_PDF_PAGES))
    cost = scan_cost_pages(page_count, conversion_mode_val)
    logger.info("scan: pages=%d, cost_pages=%d", page_count, cost)

    if user_id is None:
        remaining = FREE_ANON_PAGES - anon_used
        if cost > remaining:
            raise HTTPException(
                status_code=401,
                detail={
                    "detail": (
                        f"This scan needs {cost:,} pages. Without an account you can scan {FREE_ANON_PAGES} pages free "
                        f"({remaining} left). Create a free account to get {FREE_SIGNUP_PAGES} free pages for your first month."
                    ),
                    "code": FREE_PAGES_EXCEEDED_CODE,
                    "pages_required": cost,
                    "pages_remaining": remaining,
                },
            )
    elif cost > pages_available(billing):
        raise _insufficient_pages(cost, pages_available(billing))

    return _ScanRequest(
        content=content,
        filename=file.filename or "statement.pdf",
        user_id=user_id,
        page_count=page_count,
        cost_pages=cost,
        anon_pages_used=anon_used,
        scanned_method=scanned_method_val,
        conversion_mode=conversion_mode_val,
        incognito=incognito_mode.strip().lower() in ("true", "1", "yes"),
        ip_hash=_client_ip_hash(request),
    )


def _pdf_error(e: Exception) -> HTTPException:
    """Map a PDF decrypt/extract failure to the API error the client understands."""
    if isinstance(e, HTTPException):
        return e
    if isinstance(e, PdfPasswordRequired):
        return HTTPException(
            422,
            detail={
                "detail": "This PDF is password protected. Please enter the password to unlock it.",
                "code": PDF_PASSWORD_REQUIRED_CODE,
            },
        )
    if isinstance(e, PdfTooManyPages):
        return HTTPException(
            422,
            detail={
                "detail": (
                    f"This PDF has {e.pages:,} pages. The maximum is {e.max_pages} pages per scan. "
                    "Please split it into smaller statements (for example, a few months each) and scan them separately."
                ),
                "code": "PDF_TOO_MANY_PAGES",
            },
        )
    if isinstance(e, PdfExtractionTimeout):
        return HTTPException(
            422,
            detail={
                "detail": (
                    "This PDF took too long to read. It may be very large or complex. "
                    "Please split it into smaller statements and scan them separately."
                ),
                "code": "PDF_EXTRACTION_TIMEOUT",
            },
        )
    msg = str(e).strip()
    if isinstance(e, ValueError) and ("password" in msg.lower() or "decrypt" in msg.lower()):
        return HTTPException(422, detail={"detail": msg, "code": "PDF_PASSWORD_INCORRECT"})
    return HTTPException(422, f"PDF parsing failed: {msg}")


def _run_scan(req: _ScanRequest, progress: ProgressFn = _no_progress) -> ProcessPdfResponse:
    """The slow part of a scan (text extraction, AI, billing). Blocking: run it in a thread.

    progress(stage, chunk=None, chunks=None) is called as the scan moves through
    scan_jobs.STAGES. Raises HTTPException on failure.
    """
    try:
        return _run_scan_inner(req, progress)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("PDF processing error: %s", e)
        raise HTTPException(500, GENERIC_500_MESSAGE)


def _run_scan_inner(req: _ScanRequest, progress: ProgressFn) -> ProcessPdfResponse:
    t0 = time.perf_counter()
    user_id = req.user_id

    progress("reading")
    try:
        raw_text = extract_text_from_pdf(
            req.content,
            req.filename,
            scanned_method=req.scanned_method,
            conversion_mode=req.conversion_mode,
        )
    except Exception as e:
        raise _pdf_error(e)
    logger.info("scan: [1/3] PDF text extraction done, len=%d chars (total %.2f s)", len(raw_text), time.perf_counter() - t0)
    if not raw_text.strip():
        raise HTTPException(
            422,
            "We couldn't read any text from this PDF. Make sure it's a bank statement "
            "and not a blank or corrupted file, then try again."
        )

    progress("extracting")
    t2 = time.perf_counter()
    try:
        transactions, currency = extract_and_categorize(
            raw_text, on_chunk=lambda i, n: progress("extracting", chunk=i, chunks=n)
        )
    except Exception as e:
        logger.exception("AI extraction failed: %s", e)
        raise HTTPException(500, GENERIC_500_MESSAGE)
    logger.info("scan: [2/3] AI extraction + categorization done, transactions=%d, currency=%s (%.2f s this step, total %.2f s)", len(transactions), currency or "none", time.perf_counter() - t2, time.perf_counter() - t0)

    progress("finalizing")
    # Stored row shape: trial clients send it back for /api/email-spreadsheet (see _rows_from_trial_csv).
    csv_content = transactions_to_csv(transactions, ledger=True)
    job_id = create_job_id()
    summary = _summary_by_category(transactions)
    is_trial = user_id is None

    # Owner notification (best-effort, non-blocking): a PDF was scanned.
    try:
        scan_user = None
        if user_id:
            try:
                scan_user = get_auth_user(user_id=user_id)
            except Exception as e:  # noqa: BLE001
                logger.warning("scan notification: user lookup failed: %s", e)
        notify_scan(
            email=(scan_user or {}).get("email"),
            name=(scan_user or {}).get("full_name"),
            user_id=user_id,
            is_trial=is_trial,
            transaction_count=len(transactions),
            conversion_mode=req.conversion_mode,
            filename=req.filename,
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("scan notification failed (continuing): %s", e)

    if is_trial:
        # Record free pages for durable per-IP counting
        # (no PDF/transaction data; only a salted IP hash is stored).
        try:
            record_trial_run(job_id, req.ip_hash, pages=req.cost_pages)
        except Exception as e:
            logger.warning("trial_runs insert failed (continuing): %s", e)
        used = min(req.anon_pages_used + req.cost_pages, FREE_ANON_PAGES)
        # Return inline csv_content and raw_text
        payload = ProcessPdfResponse(
            job_id=job_id,
            transactions=[Transaction(**t) for t in transactions],
            summary_by_category=[CategorySummary(category=c, total=t) for c, t in summary],
            csv_url="",
            markdown_url="",
            currency=currency,
            csv_content=csv_content,
            raw_text=raw_text,
            trial_used=used,
            trial_limit=FREE_ANON_PAGES,
            trial_remaining=max(0, FREE_ANON_PAGES - used),
            pages_charged=req.cost_pages,
        )
        logger.info("scan: [3/3] trial finished successfully, job_id=%s (total %.2f s)", job_id, time.perf_counter() - t0)
        return payload

    billing = deduct_pages(user_id, req.cost_pages)
    if billing is None:
        current = get_billing(user_id)
        raise _insufficient_pages(req.cost_pages, pages_available(current))
    left = pages_available(billing)
    try:
        insert_usage_log(user_id, job_id, req.cost_pages, left, req.conversion_mode)
    except Exception as e:
        logger.warning("insert_usage_log failed (continuing): %s", e)
    set_job(job_id, user_id, transactions, csv_content, raw_text, currency, incognito=req.incognito, conversion_mode=req.conversion_mode)
    logger.info("scan: [3/3] finished successfully, job_id=%s, pages=%d, left=%d (total %.2f s)", job_id, req.cost_pages, left, time.perf_counter() - t0)
    return ProcessPdfResponse(
        job_id=job_id,
        transactions=[Transaction(**t) for t in transactions],
        summary_by_category=[CategorySummary(category=c, total=t) for c, t in summary],
        csv_url=f"/api/jobs/{job_id}/csv",
        markdown_url=f"/api/jobs/{job_id}/markdown",
        currency=currency,
        pages_charged=req.cost_pages,
        **_billing_fields(billing),
    )


@app.post("/api/process-pdf", response_model=ProcessPdfResponse)
@limiter.limit(_RATE_LIMIT_PROCESS_PDF)
async def process_pdf(
    request: Request,
    file: UploadFile = File(...),
    scanned_method: str = Form("vision"),
    incognito_mode: str = Form("false"),
    conversion_mode: str = Form("fast"),
    pdf_password: str | None = Form(None),
    recaptcha_token: str | None = Form(None),
    user_id: str | None = Depends(get_current_user_optional),
):
    """Synchronous scan (waits for the result). Kept for clients cached before
    /api/scans existed; new clients start a scan and poll its progress."""
    req = await _prepare_scan(request, file, scanned_method, incognito_mode, conversion_mode, pdf_password, recaptcha_token, user_id)
    return await run_in_threadpool(_run_scan, req)


# Scan failures the user caused or is told how to fix: not worth an alert.
_EXPECTED_SCAN_FAILURE_CODES = {"PDF_PASSWORD_REQUIRED", "PDF_PASSWORD_INCORRECT"}


def _report_scan_failure(scan_id: str, user_id: str | None, e: HTTPException) -> None:
    """Send failed scans to monitoring (5xx are already captured via logger.exception)."""
    if e.status_code != 422:
        return
    detail = e.detail if isinstance(e.detail, dict) else {"detail": e.detail}
    code = detail.get("code")
    if code in _EXPECTED_SCAN_FAILURE_CODES:
        return
    message = str(detail.get("detail") or "")[:120]
    logger.warning("scan %s failed (422 %s): %s", scan_id, code or "-", message)
    capture_monitoring_message(
        f"Scan failed: {code or message}",
        level="warning",
        scan_id=scan_id,
        user_id=user_id,
        status_code=str(e.status_code),
        error_code=code,
    )


def _run_scan_job(scan_id: str, req: _ScanRequest) -> None:
    def progress(stage: str, chunk: int | None = None, chunks: int | None = None) -> None:
        set_scan_stage(scan_id, stage, chunk, chunks)

    try:
        payload = _run_scan(req, progress)
        finish_scan(scan_id, jsonable_encoder(payload))
    except HTTPException as e:
        _report_scan_failure(scan_id, req.user_id, e)
        fail_scan(scan_id, e.status_code, e.detail)
    except Exception as e:  # _run_scan already maps errors; this is a last resort
        logger.exception("scan %s crashed: %s", scan_id, e)
        fail_scan(scan_id, 500, GENERIC_500_MESSAGE)


@app.options("/api/scans")
async def preflight_scans(request: Request):
    return await _preflight_response(request)


@app.post("/api/scans", status_code=202)
@limiter.limit(_RATE_LIMIT_PROCESS_PDF)
async def start_scan(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    scanned_method: str = Form("vision"),
    incognito_mode: str = Form("false"),
    conversion_mode: str = Form("fast"),
    pdf_password: str | None = Form(None),
    recaptcha_token: str | None = Form(None),
    user_id: str | None = Depends(get_current_user_optional),
):
    """Start a scan in the background and return its id. Validation, trial/credit
    checks and password errors are returned here; progress and the result come
    from GET /api/scans/{scan_id}."""
    req = await _prepare_scan(request, file, scanned_method, incognito_mode, conversion_mode, pdf_password, recaptcha_token, user_id)
    scan = create_scan(user_id)
    background_tasks.add_task(_run_scan_job, scan.id, req)
    return {"scan_id": scan.id, "status": scan.status, "stage": scan.stage}


@app.options("/api/scans/{scan_id}")
async def preflight_scan_status(request: Request):
    return await _preflight_response(request)


@app.get("/api/scans/{scan_id}")
@limiter.limit(_RATE_LIMIT_SCAN_STATUS)
async def scan_status(
    request: Request,
    scan_id: str,
    user_id: str | None = Depends(get_current_user_optional),
):
    scan = get_scan(scan_id)
    if scan is None or scan.user_id != user_id:
        raise HTTPException(404, "Scan not found")
    return scan.public()


# Each scan can be emailed in a few formats (CSV/Excel, with/without categories).
MAX_SPREADSHEET_EMAILS_PER_JOB = 4
_CSV_FIELDS = ["date", "description", "amount", "type", "category", "balance"]
_NUMERIC_FIELDS = ("amount", "balance")
_AMOUNT_RE = re.compile(r"^-?[\d,]*\.?\d*$")


def _sanitize_rows(rows: list[dict]) -> list[dict]:
    """Keep only our columns and neutralize cells a spreadsheet would run as a formula.

    Used for client-supplied data that we email, so the endpoint can't be used
    to mail arbitrary content.
    """
    clean_rows = []
    for row in rows:
        clean = {}
        for field in _CSV_FIELDS:
            value = str(row.get(field) or "").strip()
            if field in _NUMERIC_FIELDS and _AMOUNT_RE.match(value):
                clean[field] = value
            elif value[:1] in ("=", "+", "-", "@", "\t", "\r"):
                clean[field] = "'" + value
            else:
                clean[field] = value
        clean_rows.append(clean)
    return clean_rows


def _rows_from_trial_csv(csv_content: str) -> list[dict] | None:
    """Parse CSV sent by older clients; None if it doesn't have our header (with or without balance)."""
    reader = csv.DictReader(io.StringIO(csv_content))
    header = [f.strip().lower() for f in (reader.fieldnames or [])]
    if header not in (_CSV_FIELDS, _CSV_FIELDS[:-1]):
        return None
    return list(reader)


def _build_export(
    rows: list[dict], fmt: str, include_categories: bool, kind: str = "transactions", include_totals: bool = False
) -> tuple[bytes, str, str]:
    """Return (file bytes, filename, media type) for a CSV or Excel export."""
    if kind == "summary":
        summary = _summary_by_category(rows)
        if fmt == "xlsx":
            return summary_to_xlsx(summary), "statement-summary.xlsx", XLSX_MIME
        return summary_to_csv(summary).encode("utf-8"), "statement-summary.csv", "text/csv; charset=utf-8"
    suffix = "" if include_categories else "-uncategorized"
    if fmt == "xlsx":
        return transactions_to_xlsx(rows, include_categories, include_totals), f"statement{suffix}.xlsx", XLSX_MIME
    content = transactions_to_csv(rows, include_categories, include_totals).encode("utf-8")
    return content, f"statement{suffix}.csv", "text/csv; charset=utf-8"


@app.post("/api/export")
@limiter.limit(_RATE_LIMIT_EXPORT)
def export_transactions(request: Request, body: ExportRequest):
    """Build a CSV or Excel file (with or without categories) from the client's current rows.

    Stateless: it only formats the transactions the client sends (including any
    edits), so it serves both logged-in and anonymous trial users.
    """
    rows = [t.model_dump() for t in body.transactions]
    content, filename, media_type = _build_export(
        rows, body.format, body.include_categories, body.kind, body.include_totals
    )
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/api/email-spreadsheet")
@limiter.limit(_RATE_LIMIT_EMAIL_SPREADSHEET)
def email_spreadsheet(request: Request, body: EmailSpreadsheetRequest):
    """Email an anonymous trial user their spreadsheet (CSV or Excel) and store their email.

    Trial results aren't stored server-side, so the client sends the rows back.
    To stop this being an open mail relay, the job must be a recent trial run
    from the same client, each job can be emailed a limited number of times,
    and the rows are sanitized (see _sanitize_rows).
    """
    job_id = str(body.job_id)
    email = body.email.strip().lower()
    ip_hash = _client_ip_hash(request)

    if not trial_run_exists(job_id, ip_hash):
        raise HTTPException(404, "Scan not found or expired. Please scan your statement again.")
    if count_email_captures_for_job(job_id) >= MAX_SPREADSHEET_EMAILS_PER_JOB:
        raise HTTPException(429, "This spreadsheet has already been emailed. Check your inbox and spam folder.")

    if body.transactions is not None:
        rows = [t.model_dump() for t in body.transactions]
    elif body.csv_content is not None:
        rows = _rows_from_trial_csv(body.csv_content)
    else:
        rows = None
    if rows is None:
        raise HTTPException(400, "Invalid spreadsheet data.")

    content, filename, _ = _build_export(_sanitize_rows(rows), body.format, body.include_categories)
    if not send_spreadsheet_email(email, content, filename):
        raise HTTPException(502, "Couldn't send the email right now. Please download the file instead.")

    try:
        record_email_capture(email, job_id, body.marketing_opt_in, ip_hash)
    except Exception as e:
        logger.warning("email_captures insert failed (continuing): %s", e)
    try:
        notify_email_capture(email, body.marketing_opt_in)
    except Exception as e:  # noqa: BLE001
        logger.warning("email capture notification failed (continuing): %s", e)
    return {"ok": True}


@app.post("/api/feedback")
@limiter.limit(_RATE_LIMIT_FEEDBACK)
def submit_feedback(
    request: Request,
    body: FeedbackRequest,
    user_id: str | None = Depends(get_current_user_optional),
):
    """Optional feedback from the post-scan prompt (logged-in or anonymous)."""
    comment = (body.comment or "").strip() or None
    if body.rating is None and comment is None:
        raise HTTPException(400, "Pick a rating or write a comment.")
    contact_ok = body.contact_ok and user_id is not None
    job_id = str(body.job_id) if body.job_id else None
    try:
        record_feedback(user_id, job_id, body.rating, comment, contact_ok, _client_ip_hash(request))
    except Exception as e:
        logger.warning("scan_feedback insert failed (continuing): %s", e)
    # Identify the submitter for the team email: logged-in user, else the owner of the linked job.
    owner_id, via_job_link = user_id, False
    if not owner_id and job_id:
        try:
            owner_id, via_job_link = get_job_owner(job_id), True
        except Exception as e:  # noqa: BLE001
            logger.warning("feedback job owner lookup failed (continuing): %s", e)
    who = None
    if owner_id:
        try:
            who = get_auth_user(user_id=owner_id)
        except Exception as e:  # noqa: BLE001
            logger.warning("feedback user lookup failed (continuing): %s", e)
    try:
        notify_feedback(
            body.rating, comment, owner_id, contact_ok,
            email=(who or {}).get("email"), name=(who or {}).get("full_name"),
            job_id=job_id, via_job_link=via_job_link and bool(who),
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("feedback notification failed (continuing): %s", e)
    return {"ok": True}


@app.delete("/api/jobs/{job_id}/data")
def delete_job_data(job_id: uuid.UUID, user_id: str = Depends(get_current_user)):
    """Purge payload data for one job. Job row is kept."""
    job = get_job(str(job_id), user_id)
    if not job:
        raise HTTPException(404, "Job not found")
    purge_job_data(str(job_id), user_id)
    return Response(status_code=204)


@app.delete("/api/jobs/data")
def delete_jobs_data(body: PurgeJobsDataRequest, user_id: str = Depends(get_current_user)):
    """Purge payload data for multiple jobs. Job rows are kept."""
    purged = purge_jobs_data(body.job_ids, user_id)
    return Response(status_code=204, headers={"X-Purged-Count": str(purged)})


@app.get("/api/jobs/{job_id}/csv")
def download_csv(job_id: uuid.UUID, user_id: str = Depends(get_current_user)):
    job = get_job(str(job_id), user_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job.get("data_status"):
        raise HTTPException(404, "No data for this job")
    return Response(
        content=job["csv_content"],
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="statement.csv"'},
    )


@app.get("/api/jobs/{job_id}/markdown")
def download_markdown(job_id: uuid.UUID, user_id: str = Depends(get_current_user)):
    """Download the raw extracted text (e.g. Datalab markdown) for the job."""
    job = get_job(str(job_id), user_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job.get("data_status"):
        raise HTTPException(404, "No data for this job")
    raw_text = job.get("raw_text", "")
    return Response(
        content=raw_text,
        media_type="text/markdown",
        headers={"Content-Disposition": 'attachment; filename="datalab-extract.md"'},
    )


@app.post("/api/chat", response_model=ChatResponse)
@limiter.limit(_RATE_LIMIT_CHAT)
def chat(request: Request, body: ChatRequest, user_id: str = Depends(get_current_user)):
    t0 = time.perf_counter()
    job = get_job(str(body.job_id), user_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job.get("data_status"):
        raise HTTPException(404, "No data for this job")
    try:
        reply, rows = get_reply(job, body.message, [t.model_dump() for t in body.history])
        logger.info(
            "chat: job_id=%s, reply len=%d, attached rows=%d (%.2f s)",
            body.job_id, len(reply), len(rows), time.perf_counter() - t0,
        )
    except Exception as e:
        logger.exception("Chat failed: %s", e)
        raise HTTPException(500, GENERIC_500_MESSAGE)
    return ChatResponse(reply=reply, transactions=rows)


# --- Billing ---

@app.get("/api/billing/balance", response_model=BillingBalanceResponse)
def get_billing_balance(user_id: str = Depends(get_current_user)):
    """Return current page balance and subscription status."""
    billing = _load_billing(user_id)
    return BillingBalanceResponse(
        subscription_active=_subscription_active(billing),
        referral_discount=_referral_discount_info(user_id, billing),
        **_billing_fields(billing),
    )


def _referral_discount_info(user_id: str, billing: dict | None) -> dict | None:
    """Referral discount for the Account page. Plan eligibility here is a hint
    (no prior subscription on record); checkout re-checks against Stripe."""
    try:
        d = user_discount(user_id)
    except Exception as e:  # noqa: BLE001
        logger.warning("referral discount lookup failed: %s", e)
        return None
    if not d:
        return None
    return {
        "code": d["code"],
        "pct": d["pct"],
        "months": d["months"],
        "packs": d["packs"],
        "packs_ends_at": d["packs_ends_at"],
        "plan_eligible": not (billing or {}).get("stripe_subscription_id"),
    }


@app.get("/api/usage", response_model=UsageResponse)
def get_usage(
    request: Request,
    user_id: str | None = Depends(get_current_user_optional),
):
    """Page-limit state for the sidebar counter.

    Anonymous: free pages used (counted server-side per client IP).
    Signed in: free-month, plan and pack page balances.
    """
    if user_id is None:
        used = _anon_pages_used(request)
        return UsageResponse(
            authenticated=False,
            trial_used=used,
            trial_limit=FREE_ANON_PAGES,
            trial_remaining=max(0, FREE_ANON_PAGES - used),
            max_file_bytes=_max_file_size(None),
        )
    billing = _load_billing(user_id)
    return UsageResponse(
        authenticated=True,
        trial_used=0,
        trial_limit=0,
        trial_remaining=0,
        subscription_active=_subscription_active(billing),
        max_file_bytes=_max_file_size(user_id, billing),
        **_billing_fields(billing),
    )


@app.post("/api/billing/checkout-session", response_model=CheckoutSessionResponse)
def create_billing_checkout_session(body: CheckoutSessionRequest, user_id: str = Depends(get_current_user)):
    """Create Stripe Checkout session for subscription or top-up. Returns URL to redirect user."""
    if body.mode not in ("subscription", "topup"):
        raise HTTPException(400, "mode must be 'subscription' or 'topup'")
    result = create_checkout_session(
        user_id,
        body.mode,
        email=body.email,
        offer=body.offer,
        ga_client_id=body.ga_client_id,
        ga_session_id=body.ga_session_id,
        ad_opt_out=body.ad_opt_out,
        pack=body.pack,
    )
    if not result or not result.get("url"):
        raise HTTPException(502, "Could not create checkout session. Please try again.")
    return CheckoutSessionResponse(url=result["url"], sessionId=result.get("sessionId"))


# --- Paid signup (pay first, account after; see services/paid_signup.py) ---

@app.post("/api/signup/checkout", response_model=CheckoutSessionResponse)
@limiter.limit("10/minute")
def paid_signup_checkout(request: Request, body: GuestCheckoutRequest):
    """Public: Stripe subscription Checkout for a visitor without an account."""
    result = paid_signup.create_guest_checkout(
        body.referral_code, body.ga_client_id, body.ga_session_id, body.ad_opt_out
    )
    if not result or not result.get("url"):
        raise HTTPException(502, "Could not start checkout. Please try again.")
    return CheckoutSessionResponse(url=result["url"], sessionId=result.get("sessionId"))


@app.get("/api/signup/session/{session_id}")
@limiter.limit("30/minute")
def paid_signup_session(request: Request, session_id: str):
    """Public (session id is the secret): payment status + account state for /welcome."""
    try:
        return paid_signup.session_status(session_id[:255])
    except Exception as e:  # noqa: BLE001
        logger.exception("paid signup session status failed: %s", e)
        return {"status": "pending"}


@app.post("/api/signup/session/{session_id}/password")
@limiter.limit("5/minute")
def paid_signup_password(request: Request, session_id: str, body: PaidSignupPasswordRequest):
    """Set the first password on the account this paid checkout created (once)."""
    try:
        email = paid_signup.set_initial_password(session_id[:255], body.password)
    except paid_signup.PasswordError as e:
        raise HTTPException(400, str(e))
    return {"email": email}


_ADMIN_SECRET = os.environ.get("API_AUTH_SECRET", "").strip()


def _require_admin(request: Request) -> None:
    """Guard admin endpoints with a shared secret in the Authorization header."""
    if not _ADMIN_SECRET:
        raise HTTPException(503, "Admin endpoints disabled: API_AUTH_SECRET not set")
    header = request.headers.get("Authorization", "")
    token = header[7:].strip() if header.lower().startswith("bearer ") else ""
    if not token or not hmac.compare_digest(token, _ADMIN_SECRET):
        raise HTTPException(401, "Invalid admin credentials")


@app.post("/admin/generate-blog")
def admin_generate_blog(request: Request):
    """Generate one SEO blog post with Gemini + Pixabay and commit it to the repo.

    Triggered daily by a GitHub Actions cron. Protected by API_AUTH_SECRET.
    """
    _require_admin(request)
    from services.blog_generator import generate_and_publish

    try:
        result = generate_and_publish()
    except Exception as e:  # noqa: BLE001
        logger.exception("Blog generation failed")
        raise HTTPException(502, f"Blog generation failed: {e}")
    logger.info("Blog generated: %s", result.get("slug"))
    return result


# --- Affiliates ---

@app.options("/api/referral/claim")
async def preflight_referral_claim(request: Request):
    return await _preflight_response(request)


@app.options("/api/referral/{code}")
async def preflight_referral_lookup(request: Request, code: str):
    return await _preflight_response(request)


@app.get("/api/referral/{code}")
@limiter.limit("20/minute")
def referral_lookup(request: Request, code: str):
    """Public: is this a live referral code, and what discount does it give? (signup form preview)"""
    info = public_discount(code)
    if not info:
        raise HTTPException(404, "Unknown referral code")
    return info


@app.post("/api/referral/claim")
@limiter.limit("10/minute")
def referral_claim(request: Request, body: ReferralClaimRequest, user_id: str = Depends(get_current_user)):
    """Bind a just-created account to the affiliate whose code it signed up with.

    The frontend calls this once after signup (code from the signup form or a
    ?ref= link). Only accounts under services.affiliates.CLAIM_WINDOW old can
    claim, and only once. `reason` lets the UI tell a typo from a non-event.
    """
    bound, reason = claim_referral(user_id, body.code)
    return {"ok": bound, "reason": reason}


@app.get("/admin/affiliates")
def admin_list_affiliates(request: Request):
    """All affiliates with referral counts, referred revenue, pending and paid commission (cents)."""
    _require_admin(request)
    return {"affiliates": jsonable_encoder(store.list_affiliates())}


@app.post("/admin/affiliates", status_code=201)
def admin_create_affiliate(request: Request, body: AffiliateCreateRequest):
    """Set up an affiliate with their code and revenue-share percentage."""
    _require_admin(request)
    code = normalize_code(body.code)
    if not valid_code(code):
        raise HTTPException(400, "code must be 3-32 chars: letters, digits, '-' or '_'")
    try:
        row = store.create_affiliate(
            name=body.name.strip(),
            code=code,
            revenue_share_pct=body.revenue_share_pct,
            email=(body.email or "").strip() or None,
            commission_months=body.commission_months,
            notes=body.notes,
            discount_pct=body.discount_pct,
            discount_months=body.discount_months,
            discount_packs=body.discount_packs,
        )
    except psycopg2.errors.UniqueViolation:
        raise HTTPException(409, f"Code '{code}' is already taken")
    return jsonable_encoder(row)


@app.patch("/admin/affiliates/{affiliate_id}")
def admin_update_affiliate(request: Request, affiliate_id: uuid.UUID, body: AffiliateUpdateRequest):
    """Change an affiliate's terms. A new revenue_share_pct applies to future payments only."""
    _require_admin(request)
    row = store.update_affiliate(str(affiliate_id), body.model_dump(exclude_unset=True))
    if not row:
        raise HTTPException(404, "Affiliate not found")
    return jsonable_encoder(row)


@app.get("/admin/affiliates/{affiliate_id}/commissions")
def admin_list_commissions(request: Request, affiliate_id: uuid.UUID, status: str | None = None):
    """Commission ledger for one affiliate (newest first). Filter with ?status=pending|paid|void."""
    _require_admin(request)
    if status not in (None, "pending", "paid", "void"):
        raise HTTPException(400, "status must be pending, paid or void")
    return {"commissions": jsonable_encoder(store.list_commissions(str(affiliate_id), status))}


@app.post("/admin/affiliates/{affiliate_id}/payouts")
def admin_record_payout(request: Request, affiliate_id: uuid.UUID, body: AffiliatePayoutRequest):
    """After paying an affiliate, mark their pending commissions (up to `before`) paid."""
    _require_admin(request)
    return store.mark_commissions_paid(str(affiliate_id), body.before)


@app.post("/api/events/login")
def event_login(claims: dict = Depends(get_current_claims)):
    """Frontend calls this on a real SIGNED_IN so the owner gets a login email.

    Auth is the user's own verified Supabase JWT; email is read from the token.
    The frontend dedupes to avoid firing on token refresh / initial session.
    """
    try:
        user_id = claims.get("sub")
        meta = claims.get("user_metadata") or {}
        referral_code = None
        try:
            ref = get_referral_with_affiliate(user_id) if user_id else None
            referral_code = ref["code"] if ref else None
        except Exception as e:  # noqa: BLE001
            logger.warning("login notification: referral lookup failed: %s", e)
        referral_code = referral_code or normalize_code(meta.get("referral_code")) or None
        notify_login(
            email=claims.get("email"),
            user_id=user_id,
            name=name_from_metadata(meta),
            referral_code=referral_code,
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("login notification failed (continuing): %s", e)
    return {"ok": True}


_NOTIFY_WEBHOOK_SECRET = os.environ.get("NOTIFY_WEBHOOK_SECRET", "").strip()


@app.post("/api/hooks/user-created")
async def hook_user_created(request: Request):
    """Supabase Database Webhook on INSERT into auth.users -> owner signup email.

    Configure in Supabase (Database → Webhooks): table auth.users, event Insert,
    HTTP POST to this URL, with header 'X-Webhook-Secret: <NOTIFY_WEBHOOK_SECRET>'.
    """
    if not _NOTIFY_WEBHOOK_SECRET:
        raise HTTPException(503, "Signup webhook disabled: NOTIFY_WEBHOOK_SECRET not set")
    provided = request.headers.get("X-Webhook-Secret", "").strip()
    if not provided or not hmac.compare_digest(provided, _NOTIFY_WEBHOOK_SECRET):
        raise HTTPException(401, "Invalid webhook secret")
    try:
        body = await request.json()
    except Exception:
        body = {}
    record = body.get("record") if isinstance(body, dict) else None
    record = record if isinstance(record, dict) else {}
    try:
        meta = record.get("raw_user_meta_data") or {}
        notify_signup(
            email=record.get("email"),
            user_id=record.get("id"),
            name=name_from_metadata(meta),
            referral_code=normalize_code(meta.get("referral_code") if isinstance(meta, dict) else None) or None,
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("signup notification failed (continuing): %s", e)
    return {"ok": True}


@app.post("/api/billing/webhook")
async def stripe_webhook(request: Request):
    """Stripe webhook: verify signature and process invoice/subscription events."""
    payload = await request.body()
    signature = request.headers.get("Stripe-Signature", "")
    ok, msg = handle_webhook(payload, signature)
    if not ok:
        raise HTTPException(400, msg)
    return {"received": True}
