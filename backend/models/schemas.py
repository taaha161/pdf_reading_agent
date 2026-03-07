from pydantic import BaseModel
from typing import Optional


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


class ChatRequest(BaseModel):
    job_id: str
    message: str


class ChatResponse(BaseModel):
    reply: str


class JobListItem(BaseModel):
    id: str
    created_at: str
    transaction_count: int
    currency: Optional[str] = None


class JobListResponse(BaseModel):
    jobs: list[JobListItem]


class JobDetailResponse(BaseModel):
    job_id: str
    transactions: list[Transaction]
    summary_by_category: list[CategorySummary]
    currency: Optional[str] = None
