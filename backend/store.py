"""In-memory job store: job_id -> { transactions, csv_content, raw_text }."""
import uuid
from typing import Any

jobs: dict[str, dict[str, Any]] = {}


def create_job_id() -> str:
    return str(uuid.uuid4())


def set_job(job_id: str, transactions: list[dict], csv_content: str, raw_text: str = "", currency: str | None = None) -> None:
    jobs[job_id] = {
        "transactions": transactions,
        "csv_content": csv_content,
        "raw_text": raw_text,
        "currency": currency,
    }


def get_job(job_id: str) -> dict | None:
    return jobs.get(job_id)
