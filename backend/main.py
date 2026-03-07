import logging
import os
import time
from pathlib import Path

from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("pdf_processor_app")
load_dotenv(Path(__file__).resolve().parent / ".env")

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from auth import get_current_user
from models.schemas import (
    CategorySummary,
    ChatRequest,
    ChatResponse,
    JobDetailResponse,
    JobListItem,
    JobListResponse,
    ProcessPdfResponse,
    Transaction,
)
from services.chat_service import get_reply
from services.csv_export import transactions_to_csv
from services.pdf_processor import extract_text_from_pdf
from services.statement_agent import extract_and_categorize
from store import create_job_id, get_job, list_jobs, set_job

try:
    import psycopg2
except ImportError:
    psycopg2 = None

app = FastAPI(title="PDF Bank Statement Processor")


if psycopg2 is not None:
    @app.exception_handler(psycopg2.OperationalError)
    def _handle_db_unavailable(request, exc):
        """Return 503 when database is unreachable (e.g. DNS/network)."""
        return JSONResponse(
            status_code=503,
        content={"detail": "Database unavailable. Please try again later."},
        )

# CORS: allow origins from ALLOWED_ORIGINS (comma-separated); if unset, use defaults. Localhost and production are always allowed.
_VERCEL_ORIGIN = "https://pdf-reading-agent.vercel.app"
_EXTRA_ORIGINS = (
    "https://pdftoexcelconverter.io",
    "https://bankstatementscanner.com",
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


app.add_middleware(PreflightMiddleware)
app.add_middleware(AddCorsToResponseMiddleware)

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB
ALLOWED_CONTENT_TYPE = "application/pdf"


def _parse_amount(amount_str: str) -> float:
    """Parse amount string (may contain commas or leading minus) to float. Returns magnitude."""
    raw = str(amount_str or "0").replace(",", "").strip()
    try:
        return float(raw) if raw else 0.0
    except (ValueError, TypeError):
        return 0.0


def _summary_by_category(transactions: list[dict]) -> list[tuple[str, float]]:
    """Group by category; total = sum of debit amounts only (outflow) per category. Credits are not subtracted so each row shows total spent/outflow in that category."""
    totals: dict[str, float] = {}
    for t in transactions:
        magnitude = abs(_parse_amount(t.get("amount")))
        is_debit = str(t.get("type", "")).lower() == "debit"
        if not is_debit:
            magnitude = 0.0  # Only count debits (outflows) in the summary total
        cat = str(t.get("category", "")).strip() or "Other"
        totals[cat] = totals.get(cat, 0) + magnitude
    return sorted(totals.items(), key=lambda x: -x[1])


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
async def preflight_job_detail(request: Request, job_id: str):
    return await _preflight_response(request)


@app.options("/api/jobs/{job_id}/csv")
async def preflight_csv(request: Request, job_id: str):
    return await _preflight_response(request)


@app.options("/api/jobs/{job_id}/markdown")
async def preflight_markdown(request: Request, job_id: str):
    return await _preflight_response(request)


@app.get("/api/jobs", response_model=JobListResponse)
def list_user_jobs(user_id: str = Depends(get_current_user)):
    """List current user's jobs (newest first)."""
    jobs = list_jobs(user_id)
    return JobListResponse(jobs=[JobListItem(**j) for j in jobs])


@app.get("/api/jobs/{job_id}", response_model=JobDetailResponse)
def get_job_detail(job_id: str, user_id: str = Depends(get_current_user)):
    """Get one job's data for viewing (transactions + summary)."""
    job = get_job(job_id, user_id)
    if not job:
        raise HTTPException(404, "Job not found")
    summary = _summary_by_category(job["transactions"])
    return JobDetailResponse(
        job_id=job_id,
        transactions=[Transaction(**t) for t in job["transactions"]],
        summary_by_category=[CategorySummary(category=c, total=t) for c, t in summary],
        currency=job.get("currency"),
    )


@app.post("/api/process-pdf", response_model=ProcessPdfResponse)
async def process_pdf(
    file: UploadFile = File(...),
    scanned_method: str = Form("vision"),
    user_id: str = Depends(get_current_user),
):
    t0 = time.perf_counter()
    # Normalize: only "ocr" or "vision" (for scanned PDFs)
    if scanned_method and scanned_method.strip().lower() == "ocr":
        scanned_method_val = "ocr"
    else:
        scanned_method_val = "vision"
    logger.info("process-pdf: request started, filename=%s, scanned_method=%s", file.filename or "statement.pdf", scanned_method_val)
    try:
        if file.content_type and file.content_type != ALLOWED_CONTENT_TYPE:
            raise HTTPException(400, "File must be a PDF")
        content = await file.read()
        logger.info("process-pdf: file read, size=%d bytes (%.2f s)", len(content), time.perf_counter() - t0)
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(400, "File too large")
        if not content:
            raise HTTPException(400, "Empty file")

        t1 = time.perf_counter()
        try:
            raw_text = extract_text_from_pdf(content, file.filename or "statement.pdf", scanned_method=scanned_method_val)
        except Exception as e:
            raise HTTPException(422, f"PDF parsing failed: {str(e)}")
        logger.info("process-pdf: PDF text extraction done, len=%d chars (%.2f s)", len(raw_text), time.perf_counter() - t1)
        if not raw_text.strip():
            raise HTTPException(
                422,
                "Could not extract text from PDF (empty or image-only). "
                "For scanned PDFs, install poppler and Tesseract (see README)."
            )

        t2 = time.perf_counter()
        try:
            transactions, currency = extract_and_categorize(raw_text)
        except Exception as e:
            raise HTTPException(500, f"Failed to process statement with AI: {str(e)}")
        logger.info("process-pdf: AI extraction + categorization done, transactions=%d, currency=%s (%.2f s)", len(transactions), currency or "none", time.perf_counter() - t2)

        csv_content = transactions_to_csv(transactions)
        job_id = create_job_id()
        set_job(job_id, user_id, transactions, csv_content, raw_text, currency)
        summary = _summary_by_category(transactions)
        logger.info("process-pdf: finished successfully, job_id=%s, total=%.2f s", job_id, time.perf_counter() - t0)

        return ProcessPdfResponse(
            job_id=job_id,
            transactions=[Transaction(**t) for t in transactions],
            summary_by_category=[CategorySummary(category=c, total=t) for c, t in summary],
            csv_url=f"/api/jobs/{job_id}/csv",
            markdown_url=f"/api/jobs/{job_id}/markdown",
            currency=currency,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Server error while processing PDF: {str(e)}")


@app.get("/api/jobs/{job_id}/csv")
def download_csv(job_id: str, user_id: str = Depends(get_current_user)):
    job = get_job(job_id, user_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return Response(
        content=job["csv_content"],
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="statement.csv"'},
    )


@app.get("/api/jobs/{job_id}/markdown")
def download_markdown(job_id: str, user_id: str = Depends(get_current_user)):
    """Download the raw extracted text (e.g. Datalab markdown) for the job."""
    job = get_job(job_id, user_id)
    if not job:
        raise HTTPException(404, "Job not found")
    raw_text = job.get("raw_text", "")
    return Response(
        content=raw_text,
        media_type="text/markdown",
        headers={"Content-Disposition": 'attachment; filename="datalab-extract.md"'},
    )


@app.post("/api/chat", response_model=ChatResponse)
def chat(body: ChatRequest, user_id: str = Depends(get_current_user)):
    t0 = time.perf_counter()
    job = get_job(body.job_id, user_id)
    if not job:
        raise HTTPException(404, "Job not found")
    try:
        reply = get_reply(job, body.message)
        logger.info("chat: job_id=%s, reply len=%d (%.2f s)", body.job_id, len(reply), time.perf_counter() - t0)
    except Exception as e:
        raise HTTPException(500, f"Chat failed: {str(e)}")
    return ChatResponse(reply=reply)
