import uuid
from typing import Optional

from pydantic import BaseModel, Field


class Transaction(BaseModel):
    date: str
    description: str
    amount: str
    type: str  # credit or debit
    category: str


class CategorySummary(BaseModel):
    category: str
    total: float


class ProcessPdfResponse(BaseModel):
    job_id: str
    transactions: list[Transaction]
    summary_by_category: list[CategorySummary]
    csv_url: str
    markdown_url: str
    currency: Optional[str] = None  # Inferred from statement (e.g. USD, PKR); None if unknown
    csv_content: Optional[str] = None  # Set for trial (no job stored); client uses for download
    raw_text: Optional[str] = None  # Set for trial; client uses for markdown download


class ChatRequest(BaseModel):
    job_id: uuid.UUID
    message: str = Field(..., min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    reply: str


class JobListItem(BaseModel):
    id: str
    created_at: str
    transaction_count: int
    currency: Optional[str] = None
    has_payload: bool = True  # False when incognito or payload was purged


class JobListResponse(BaseModel):
    jobs: list[JobListItem]


class JobDetailResponse(BaseModel):
    job_id: str
    transactions: list[Transaction]
    summary_by_category: list[CategorySummary]
    currency: Optional[str] = None
    data_status: Optional[str] = None  # "incognito" | "purged" when no payload


class PurgeJobsDataRequest(BaseModel):
    job_ids: list[str]
