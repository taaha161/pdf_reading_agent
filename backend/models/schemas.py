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
    # Fresh scan-limit state so the client can update the counter immediately,
    # without a follow-up /api/usage call (the trial cookie is cross-site and may
    # be blocked, so we can't rely on it being read back).
    trial_used: Optional[int] = None
    trial_limit: Optional[int] = None
    trial_remaining: Optional[int] = None
    balance_cents: Optional[int] = None


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
    conversion_mode: Optional[str] = None  # fast | balanced | accurate


class DashboardStats(BaseModel):
    total_income: float
    total_expenses: float
    surplus: float
    summary_by_category: list[CategorySummary]
    primary_currency: Optional[str] = None


class JobListResponse(BaseModel):
    jobs: list[JobListItem]
    stats: Optional[DashboardStats] = None


class JobDetailResponse(BaseModel):
    job_id: str
    transactions: list[Transaction]
    summary_by_category: list[CategorySummary]
    currency: Optional[str] = None
    data_status: Optional[str] = None  # "incognito" | "purged" when no payload
    conversion_mode: Optional[str] = None  # fast | balanced | accurate


class UpdateJobTransactionsRequest(BaseModel):
    transactions: list[Transaction]


class BillingBalanceResponse(BaseModel):
    balance_cents: int
    subscription_active: bool


class UsageResponse(BaseModel):
    """Scan-limit state for the sidebar counter (works for trial + authenticated users)."""
    authenticated: bool
    trial_used: int
    trial_limit: int
    trial_remaining: int
    balance_cents: Optional[int] = None  # only for authenticated users
    subscription_active: bool = False


class CheckoutSessionRequest(BaseModel):
    mode: str  # "subscription" | "topup"
    email: Optional[str] = None  # optional, for Stripe Customer


class CheckoutSessionResponse(BaseModel):
    url: str
    sessionId: Optional[str] = None


class PurgeJobsDataRequest(BaseModel):
    job_ids: list[str]
