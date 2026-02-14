import os
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env")

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from models.schemas import CategorySummary, ChatRequest, ChatResponse, ProcessPdfResponse, Transaction
from services.chat_service import get_reply
from services.csv_export import transactions_to_csv
from services.pdf_processor import extract_text_from_pdf
from services.statement_agent import extract_and_categorize
from store import create_job_id, get_job, set_job

app = FastAPI(title="PDF Bank Statement Processor")

# CORS: set ALLOWED_ORIGINS on Render to your frontend URL, e.g. https://pdf-reading-agent.vercel.app
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

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


@app.post("/api/process-pdf", response_model=ProcessPdfResponse)
async def process_pdf(file: UploadFile = File(...)):
    try:
        if file.content_type and file.content_type != ALLOWED_CONTENT_TYPE:
            raise HTTPException(400, "File must be a PDF")
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(400, "File too large")
        if not content:
            raise HTTPException(400, "Empty file")

        try:
            raw_text = extract_text_from_pdf(content, file.filename or "statement.pdf")
        except Exception as e:
            raise HTTPException(422, f"PDF parsing failed: {str(e)}")
        if not raw_text.strip():
            raise HTTPException(
                422,
                "Could not extract text from PDF (empty or image-only). "
                "For scanned PDFs, install poppler and Tesseract (see README)."
            )

        try:
            transactions = extract_and_categorize(raw_text)
        except Exception as e:
            raise HTTPException(500, f"Failed to process statement with AI: {str(e)}")
        csv_content = transactions_to_csv(transactions)
        job_id = create_job_id()
        set_job(job_id, transactions, csv_content)

        summary = _summary_by_category(transactions)

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
    job = get_job(body.job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    try:
        reply = get_reply(job, body.message)
    except Exception as e:
        raise HTTPException(500, f"Chat failed: {str(e)}")
    return ChatResponse(reply=reply)
