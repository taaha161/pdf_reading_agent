from datetime import datetime
import uuid
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from services.text_clean import clean_description


class Transaction(BaseModel):
    date: str
    description: str
    amount: str
    type: str  # credit or debit
    category: str
    # Account balance after this row (printed on the statement or worked out from the nearest
    # printed one); blank when the statement has no balances. Older jobs don't have it.
    balance: Optional[str] = ""
    # True when the balance was printed on the statement, False when it was worked out.
    # None for rows saved before this existed. Reconciliation only checks printed balances.
    balance_printed: Optional[bool] = None


class ReconciliationCheck(BaseModel):
    key: Literal["balance_chain", "opening", "closing", "credits", "debits"]
    status: Literal["pass", "fail", "skipped"]
    expected: Optional[float] = None  # what the statement says
    actual: Optional[float] = None  # what the extracted rows add up to
    difference: Optional[float] = None  # expected - actual
    breaks: Optional[int] = None  # balance_chain: steps between printed balances that don't add up


class ReconciliationHint(BaseModel):
    kind: Literal["flipped_type", "duplicate_row", "missing_row"]
    row_index: Optional[int] = None  # flipped_type / duplicate_row: the suspect row
    from_row: Optional[int] = None  # missing_row: it belongs between these two rows
    to_row: Optional[int] = None
    amount: float
    direction: Optional[Literal["credit", "debit"]] = None  # missing_row


class Reconciliation(BaseModel):
    status: Literal["reconciled", "mismatch", "unverified"]
    reason: Optional[str] = None  # user-facing, set when unverified
    opening_balance: Optional[float] = None
    closing_balance: Optional[float] = None
    total_credits: float
    total_debits: float
    checks: list[ReconciliationCheck] = Field(default_factory=list)
    hints: list[ReconciliationHint] = Field(default_factory=list)


class CategorySummary(BaseModel):
    category: str
    total: float


class ProcessPdfResponse(BaseModel):
    job_id: str
    transactions: list[Transaction]
    summary_by_category: list[CategorySummary]
    csv_url: str
    markdown_url: str
    reconciliation: Optional[Reconciliation] = None
    currency: Optional[str] = None  # Inferred from statement (e.g. USD, PKR); None if unknown
    csv_content: Optional[str] = None  # Set for trial (no job stored); client uses for download
    raw_text: Optional[str] = None  # Set for trial; client uses for markdown download
    # Fresh scan-limit state so the client can update the counter immediately,
    # without a follow-up /api/usage call (the trial cookie is cross-site and may
    # be blocked, so we can't rely on it being read back).
    trial_used: Optional[int] = None
    trial_limit: Optional[int] = None
    trial_remaining: Optional[int] = None
    pages_charged: Optional[int] = None  # pages this scan cost
    pages_remaining: Optional[int] = None  # signed in only
    free_pages: Optional[int] = None
    free_expires_at: Optional[datetime] = None
    plan_pages: Optional[int] = None
    pack_pages: Optional[int] = None


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field("", max_length=20_000)


class ChatRequest(BaseModel):
    job_id: uuid.UUID
    message: str = Field(..., min_length=1, max_length=4000)
    # Earlier turns of this chat (oldest first) so follow-ups like "download those" work.
    history: list[ChatTurn] = Field(default_factory=list, max_length=20)


class FetchPdfUrlRequest(BaseModel):
    url: str = Field(..., min_length=1, max_length=2048)


class ChatResponse(BaseModel):
    reply: str
    # Rows the assistant attached for download (date, description, amount, type, category, and
    # "group" when the question grouped people/merchants); empty if none.
    transactions: list[dict[str, str]] = Field(default_factory=list)


class JobListItem(BaseModel):
    id: str
    created_at: str
    transaction_count: int
    currency: Optional[str] = None
    has_payload: bool = True  # False when incognito or payload was purged
    conversion_mode: Optional[str] = None  # fast | balanced | accurate
    reconciliation_status: Optional[Literal["reconciled", "mismatch", "unverified"]] = None  # None without data
    bank_name: Optional[str] = None  # from the statement's summary, when read
    account_last4: Optional[str] = None
    period_end: Optional[str] = None  # YYYY-MM-DD


class DashboardStats(BaseModel):
    total_income: float
    total_expenses: float
    surplus: float
    summary_by_category: list[CategorySummary]
    primary_currency: Optional[str] = None


class AccountStatement(BaseModel):
    job_id: str
    period_start: Optional[str] = None  # YYYY-MM-DD
    period_end: str
    opening_balance: Optional[float] = None
    closing_balance: Optional[float] = None
    status: Literal["reconciled", "mismatch", "unverified"]


class AccountLink(BaseModel):
    from_job: str
    to_job: str
    kind: Literal["ok", "gap", "balance_mismatch", "duplicate"]
    missing_from: Optional[str] = None  # gap: the dates no saved statement covers
    missing_to: Optional[str] = None
    difference: Optional[float] = None  # balance_mismatch: next opening - previous closing


class Account(BaseModel):
    """One bank account or card, with its saved statements oldest first (see reconciliation.account_continuity)."""
    bank_name: Optional[str] = None
    account_last4: str
    currency: Optional[str] = None
    account_type: Literal["bank", "credit_card"]
    statements: list[AccountStatement]
    links: list[AccountLink]


class JobListResponse(BaseModel):
    jobs: list[JobListItem]
    stats: Optional[DashboardStats] = None
    accounts: list[Account] = Field(default_factory=list)
    # Saved statements we couldn't place in an account (no account number or period read).
    unmatched_job_ids: list[str] = Field(default_factory=list)


class JobDetailResponse(BaseModel):
    job_id: str
    transactions: list[Transaction]
    summary_by_category: list[CategorySummary]
    reconciliation: Optional[Reconciliation] = None  # None when the job has no saved data
    currency: Optional[str] = None
    data_status: Optional[str] = None  # "incognito" | "purged" when no payload
    conversion_mode: Optional[str] = None  # fast | balanced | accurate


class UpdateJobTransactionsRequest(BaseModel):
    transactions: list[Transaction]


class ReferralDiscount(BaseModel):
    code: str
    pct: float  # percent off
    months: Optional[int] = None  # plan discount length once subscribed; None = forever
    packs: bool = False  # page packs discounted right now
    packs_ends_at: Optional[datetime] = None
    plan_eligible: bool = True  # False once they've subscribed before (plan discount is first subscription only)


class BillingBalanceResponse(BaseModel):
    subscription_active: bool
    referral_discount: Optional[ReferralDiscount] = None
    pages_remaining: int = 0  # free (unexpired) + plan + pack
    free_pages: int = 0  # free-month pages left (0 once expired)
    free_expires_at: Optional[datetime] = None
    plan_pages: int = 0  # monthly plan pages left this cycle
    pack_pages: int = 0  # purchased pages (never expire)
    frozen_pages: int = 0  # subscriber pack pages paused until they subscribe again


class UsageResponse(BaseModel):
    """Page-limit state for the sidebar counter (works for anonymous + authenticated users).
    trial_* are anonymous free pages (used / limit / remaining)."""
    authenticated: bool
    trial_used: int
    trial_limit: int
    trial_remaining: int
    pages_remaining: Optional[int] = None  # authenticated only (free + plan + pack)
    free_pages: Optional[int] = None
    free_expires_at: Optional[datetime] = None
    plan_pages: Optional[int] = None
    pack_pages: Optional[int] = None
    frozen_pages: Optional[int] = None
    subscription_active: bool = False
    max_file_bytes: int = 20 * 1024 * 1024  # upload limit for this caller's tier
    review_claim: Optional[str] = None  # authenticated only: None | pending | granted | rejected
    scan_count: Optional[int] = None  # authenticated only: scans run (review card shows after a few)


class CheckoutSessionRequest(BaseModel):
    mode: str  # "subscription" | "topup"
    email: Optional[str] = None  # optional, for Stripe Customer
    offer: Optional[str] = None  # ad-campaign offer code (see billing.OFFERS); validated server-side
    pack: Optional[str] = None  # topup only: page pack id (see billing.PAGE_PACKS): "10" | "30" | "100" (subscribers) | "450"
    ga_client_id: Optional[str] = Field(default=None, max_length=64)  # GA4 ids for server-side subscribe/purchase events
    ga_session_id: Optional[str] = Field(default=None, max_length=64)
    ad_opt_out: bool = False  # browser sent Global Privacy Control: no ad-platform conversions


class GuestCheckoutRequest(BaseModel):
    """Pricing page "Get Monthly" with no account (paid signup: pay first, account after)."""
    referral_code: Optional[str] = Field(default=None, max_length=32)
    ga_client_id: Optional[str] = Field(default=None, max_length=64)
    ga_session_id: Optional[str] = Field(default=None, max_length=64)
    ad_opt_out: bool = False


class PaidSignupPasswordRequest(BaseModel):
    password: str = Field(min_length=1, max_length=128)


class CheckoutSessionResponse(BaseModel):
    url: str
    sessionId: Optional[str] = None


class PurgeJobsDataRequest(BaseModel):
    job_ids: list[str]


ExportFormat = Literal["csv", "xlsx"]
# "summary" exports the category totals table instead of the transaction rows.
ExportKind = Literal["transactions", "summary"]
MAX_EXPORT_TRANSACTIONS = 20_000


class ExportTransaction(BaseModel):
    """Lenient transaction row for exports (client-side rows may have blanks/nulls)."""
    date: Optional[str] = ""
    description: Optional[str] = Field("", max_length=2000)
    amount: Optional[str] = ""
    type: Optional[str] = ""
    category: Optional[str] = ""
    balance: Optional[str] = ""
    # Chat downloads grouped by person/merchant ("John", "Alice"); adds a Group column and group totals.
    group: Optional[str] = Field("", max_length=200)

    @field_validator("description")
    @classmethod
    def _clean_description(cls, v):
        # Every download path builds files from these rows, so statement icons are dropped here.
        return clean_description(v)


class ExportRequest(BaseModel):
    transactions: list[ExportTransaction] = Field(..., max_length=MAX_EXPORT_TRANSACTIONS)
    format: ExportFormat = "csv"
    include_categories: bool = True
    kind: ExportKind = "transactions"
    # Append count / money in / money out / net under the rows (chat downloads). Off by default so
    # files for QuickBooks/Xero imports stay rows-only.
    include_totals: bool = False
    # Excel only: the scan's reconciliation, written to a separate "Reconciliation" sheet.
    reconciliation: Optional[Reconciliation] = None


MAX_BULK_STATEMENTS = 50
MAX_BULK_TRANSACTIONS = 100_000


class BulkExportStatement(BaseModel):
    """One scanned statement in a combined (bulk upload) download."""
    name: str = Field(..., min_length=1, max_length=255)  # usually the PDF's file name
    transactions: list[ExportTransaction] = Field(..., max_length=MAX_EXPORT_TRANSACTIONS)


class BulkExportRequest(BaseModel):
    """Several statements in one file: a combined sheet with a Statement column (+ a sheet each in Excel)."""
    statements: list[BulkExportStatement] = Field(..., min_length=1, max_length=MAX_BULK_STATEMENTS)
    format: ExportFormat = "xlsx"
    include_categories: bool = True

    @model_validator(mode="after")
    def _total_rows(self):
        if sum(len(s.transactions) for s in self.statements) > MAX_BULK_TRANSACTIONS:
            raise ValueError(f"At most {MAX_BULK_TRANSACTIONS} transactions in one download")
        return self


class EmailSpreadsheetRequest(BaseModel):
    job_id: uuid.UUID
    email: str = Field(..., min_length=3, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    # New clients send transactions; csv_content is kept for clients deployed before export options.
    transactions: Optional[list[ExportTransaction]] = Field(None, max_length=MAX_EXPORT_TRANSACTIONS)
    csv_content: Optional[str] = Field(None, min_length=1, max_length=2_000_000)
    format: ExportFormat = "csv"
    include_categories: bool = True
    marketing_opt_in: bool = False
    reconciliation: Optional[Reconciliation] = None  # Excel only, see ExportRequest


class FeedbackRequest(BaseModel):
    job_id: Optional[uuid.UUID] = None
    rating: Optional[int] = Field(None, ge=1, le=5)
    comment: Optional[str] = Field(None, max_length=2000)
    contact_ok: bool = False


class ReviewClaimRequest(BaseModel):
    """Claim the review reward. proof = link to the review or the name it was posted under."""
    platform: Literal["g2"] = "g2"
    proof: str = Field(..., min_length=2, max_length=500)


# --- Affiliates ---

class ReferralClaimRequest(BaseModel):
    code: str = Field(max_length=64)


class AffiliateCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    code: str = Field(max_length=32)  # 3-32 chars: a-z, 0-9, '-', '_' (stored lowercase)
    revenue_share_pct: float = Field(ge=0, le=100)  # % of each payment by a referred user
    email: Optional[str] = Field(default=None, max_length=320)
    commission_months: Optional[int] = Field(default=None, gt=0)  # None = lifetime
    notes: Optional[str] = Field(default=None, max_length=2000)
    # Discount for users who sign up with the code. 0 = no discount.
    discount_pct: float = Field(default=0, ge=0, le=100)  # % off the monthly plan (and packs if discount_packs)
    discount_months: Optional[int] = Field(default=None, gt=0)  # plan: months from subscribing; packs: months from signup. None = forever
    discount_packs: bool = False


class AffiliateUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    revenue_share_pct: Optional[float] = Field(default=None, ge=0, le=100)  # applies to future payments only
    email: Optional[str] = Field(default=None, max_length=320)
    commission_months: Optional[int] = Field(default=None, gt=0)
    discount_pct: Optional[float] = Field(default=None, ge=0, le=100)  # new subscriptions only; existing keep their coupon
    discount_months: Optional[int] = Field(default=None, gt=0)
    discount_packs: Optional[bool] = None
    active: Optional[bool] = None
    notes: Optional[str] = Field(default=None, max_length=2000)


class AffiliatePayoutRequest(BaseModel):
    before: Optional[datetime] = None  # mark pending commissions up to this time paid (default: now)
