"""Chat service: answer user questions about a job's CSV/transactions using Gemini."""
import os
from typing import Any

from google import genai
from google.genai.types import GenerateContentConfig

SYSTEM_INSTRUCTION = (
    "You are a helpful assistant that explains and validates bank statement data. "
    "Answer ONLY based on the CSV/transaction data provided. "
    "Justify categories and data when asked (e.g. why a row was categorized as X). "
    "Be concise and accurate."
)


def _get_client() -> genai.Client:
    api_key = os.environ.get("GOOGLE_GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "GOOGLE_GEMINI_API_KEY is not set. Set it in .env for chat and extraction."
        )
    return genai.Client(api_key=api_key)


def get_reply(job_data: dict[str, Any], message: str) -> str:
    """
    Build prompt with job's CSV/transactions and user message; return Gemini reply.
    job_data: { "transactions": [...], "csv_content": "..." }
    """
    csv_content = job_data.get("csv_content", "")
    if not csv_content:
        csv_content = "No transaction data available."

    client = _get_client()
    user_content = (
        f"Statement data (CSV):\n{csv_content[:15000]}\n\nUser question: {message}"
    )
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=user_content,
        config=GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0,
        ),
    )
    return (response.text or "").strip()
