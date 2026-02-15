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

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from models.schemas import CategorySummary, ChatRequest, ChatResponse, ProcessPdfResponse, Transaction
from services.chat_service import get_reply
from services.csv_export import transactions_to_csv
from services.pdf_processor import extract_text_from_pdf
from services.statement_agent import extract_and_categorize
from store import create_job_id, get_job, set_job

app = FastAPI(title="PDF Bank Statement Processor")

# CORS: allow origins from ALLOWED_ORIGINS (comma-separated); if unset, use defaults. Production frontend is always allowed.
_VERCEL_ORIGIN = "https://pdf-reading-agent.vercel.app"
_origins_raw = os.environ.get("ALLOWED_ORIGINS", "").strip()
if _origins_raw:
    _origins_list = [o.strip().rstrip("/") for o in _origins_raw.split(",") if o.strip()]
else:
    _origins_list = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ]
if _VERCEL_ORIGIN not in _origins_list:
    _origins_list.append(_VERCEL_ORIGIN)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


def _cors_headers(origin: str) -> dict:
    """CORS headers to attach when origin is allowed (same as the extension would allow)."""
    return {
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, HEAD, OPTIONS, PATCH",
        "Access-Control-Allow-Headers": "*",
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Max-Age": "86400",
    }


class PreflightMiddleware(BaseHTTPMiddleware):
    """Handle all OPTIONS (preflight) here with 200 + CORS so the router is never hit (avoids 400). Actual response CORS still enforced by AddCorsToResponseMiddleware."""

    async def dispatch(self, request: Request, call_next):
        if request.method != "OPTIONS":
            return await call_next(request)
        origin = request.headers.get("origin", "") or "*"
        return Response(status_code=200, headers=_cors_headers(origin))


class AddCorsToResponseMiddleware(BaseHTTPMiddleware):
    """Add CORS headers to every response when request Origin is in allowed list (so browser never blocks)."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        origin = request.headers.get("origin", "")
        if origin and origin in _origins_list:
            for key, value in _cors_headers(origin).items():
                response.headers[key] = value
        return response


app.add_middleware(PreflightMiddleware)
app.add_middleware(AddCorsToResponseMiddleware)

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB
ALLOWED_CONTENT_TYPE = "application/pdf"


def _summary_by_category(transactions: list[dict]) -> list[tuple[str, float]]:
    """Group transactions by category and sum amounts (debit positive, credit negative)."""
    totals: dict[str, float] = {}
    for t in transactions:
        try:
            raw = str(t.get("amount", "0")).replace(",", "").strip()
            val = float(raw) if raw else 0.0
        except (ValueError, TypeError):
            val = 0.0
        if str(t.get("type", "")).lower() == "credit":
            val = -val
        cat = str(t.get("category", "")).strip() or "Other"
        totals[cat] = totals.get(cat, 0) + val
    return sorted(totals.items(), key=lambda x: -abs(x[1]))


@app.get("/health")
def health():
    return {"status": "ok"}


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


@app.options("/api/jobs/{job_id}/csv")
async def preflight_csv(request: Request, job_id: str):
    return await _preflight_response(request)


@app.post("/api/process-pdf", response_model=ProcessPdfResponse)
async def process_pdf(file: UploadFile = File(...)):
    t0 = time.perf_counter()
    logger.info("process-pdf: request started, filename=%s", file.filename or "statement.pdf")
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
            raw_text = extract_text_from_pdf(content, file.filename or "statement.pdf")
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
            transactions = extract_and_categorize(raw_text)
        except Exception as e:
            raise HTTPException(500, f"Failed to process statement with AI: {str(e)}")
        logger.info("process-pdf: AI extraction + categorization done, transactions=%d (%.2f s)", len(transactions), time.perf_counter() - t2)

        csv_content = transactions_to_csv(transactions)
        job_id = create_job_id()
        set_job(job_id, transactions, csv_content)
        summary = _summary_by_category(transactions)
        logger.info("process-pdf: finished successfully, job_id=%s, total=%.2f s", job_id, time.perf_counter() - t0)

        return ProcessPdfResponse(
            job_id=job_id,
            transactions=[Transaction(**t) for t in transactions],
            summary_by_category=[CategorySummary(category=c, total=t) for c, t in summary],
            csv_url=f"/api/jobs/{job_id}/csv",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Server error while processing PDF: {str(e)}")


@app.get("/api/jobs/{job_id}/csv")
def download_csv(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return Response(
        content=job["csv_content"],
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="statement.csv"'},
    )


@app.post("/api/chat", response_model=ChatResponse)
def chat(body: ChatRequest):
    t0 = time.perf_counter()
    job = get_job(body.job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    try:
        reply = get_reply(job, body.message)
        logger.info("chat: job_id=%s, reply len=%d (%.2f s)", body.job_id, len(reply), time.perf_counter() - t0)
    except Exception as e:
        raise HTTPException(500, f"Chat failed: {str(e)}")
    return ChatResponse(reply=reply)
