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


class ChatRequest(BaseModel):
    job_id: str
    message: str


class ChatResponse(BaseModel):
    reply: str
