"""Validate/edit service: interpret user message as either a reply or an apply_edit using Gemini structured output."""
import json
import logging
import os
from typing import Any

from google import genai
from google.genai.types import GenerateContentConfig

from services.csv_export import transactions_to_csv

logger = logging.getLogger("pdf_processor_app")

SYSTEM_INSTRUCTION = """You are a helpful assistant for a bank statement app. The user can either:
1. Ask a question about the transactions (e.g. "Why is Amazon in Shopping?", "What's my total food spending?") -> use action "reply" with a concise, accurate answer based only on the data.
2. Ask to change or recategorize transactions (e.g. "Add chase transactions into business category", "Change all Amazon to Shopping", "Recategorize Starbucks as Food") -> use action "apply_edit" and return the FULL list of transactions with the requested changes applied. Keep every transaction; only modify the fields the user asked to change (usually category). Preserve date, description, amount, type exactly unless the user asks to change them.

You are given the current transactions as JSON. For apply_edit, output the complete modified transactions array with the same structure: each object has "date", "description", "amount", "type", "category" (all strings). Match the exact keys and types. Do not add or remove transactions unless the user explicitly asks to. For recategorization, only change the "category" field for the matching rows."""

# JSON schema for structured output: either reply or apply_edit with full transactions list
VALIDATE_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["reply", "apply_edit"]},
        "text": {"type": "string", "description": "Required when action is reply. The answer to the user's question."},
        "transactions": {
            "type": "array",
            "description": "Required when action is apply_edit. The full list of transactions with edits applied.",
            "items": {
                "type": "object",
                "properties": {
                    "date": {"type": "string"},
                    "description": {"type": "string"},
                    "amount": {"type": "string"},
                    "type": {"type": "string"},
                    "category": {"type": "string"},
                },
                "required": ["date", "description", "amount", "type", "category"],
            },
        },
    },
    "required": ["action"],
}


def _get_client() -> genai.Client:
    api_key = os.environ.get("GOOGLE_GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "GOOGLE_GEMINI_API_KEY is not set. Set it in .env for validate/edit."
        )
    return genai.Client(api_key=api_key)


def validate_and_apply(
    job_data: dict[str, Any], message: str
) -> tuple[str, list[dict[str, Any]] | None]:
    """
    Interpret user message: either return (action="reply", text, None) or (action="apply_edit", message, transactions).
    job_data: { "transactions": [...], "csv_content": "..." }
    Returns: (response_type, content) where content is either the reply text or the updated transactions list.
    """
    transactions = job_data.get("transactions") or []
    csv_content = job_data.get("csv_content", "")
    if not csv_content and transactions:
        csv_content = transactions_to_csv(transactions)
    if not csv_content:
        csv_content = "No transaction data available."

    # Limit context size
    user_content = (
        f"Current transactions (CSV):\n{csv_content[:20000]}\n\nUser message: {message}"
    )

    client = _get_client()
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=user_content,
        config=GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0,
            response_mime_type="application/json",
            response_json_schema=VALIDATE_RESPONSE_SCHEMA,
        ),
    )
    text = (response.text or "").strip()
    if not text:
        return "message", "I couldn't process that. Please try again."

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        logger.warning("validate_edit: invalid JSON from Gemini: %s", e)
        return "message", "Something went wrong. Please try again."

    action = (data.get("action") or "").strip().lower()
    if action == "reply":
        return "message", (data.get("text") or "").strip() or "No reply generated."
    if action == "apply_edit":
        txs = data.get("transactions")
        if not isinstance(txs, list):
            return "message", "I couldn't apply that change. Please try again."
        # Normalize to list of dicts with required keys
        out = []
        for t in txs:
            if not isinstance(t, dict):
                continue
            out.append({
                "date": str(t.get("date", "")),
                "description": str(t.get("description", "")),
                "amount": str(t.get("amount", "")),
                "type": str(t.get("type", "")).lower() or "debit",
                "category": str(t.get("category", "")).strip() or "Other",
            })
        if len(out) != len(transactions):
            logger.warning(
                "validate_edit: apply_edit returned %d transactions, expected %d; using reply fallback",
                len(out),
                len(transactions),
            )
            return "message", "I couldn't apply that change without changing the number of transactions. Please be more specific."
        return "transactions_updated", out
    return "message", (data.get("text") or "I didn't understand. You can ask a question or ask to recategorize transactions.").strip()
