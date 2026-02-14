"""Chat service: answer user questions about a job's CSV/transactions using LLM context."""
import os
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

try:
    from langchain_groq import ChatGroq
    _GROQ_AVAILABLE = True
except ImportError:
    _GROQ_AVAILABLE = False
from langchain_community.chat_models import ChatOllama


def _get_llm():
    api_key = os.environ.get("GROQ_API_KEY")
    if api_key and _GROQ_AVAILABLE:
        return ChatGroq(model="llama-3.1-8b-instant", api_key=api_key, temperature=0)
    return ChatOllama(model="llama3.2", temperature=0)


def get_reply(job_data: dict[str, Any], message: str) -> str:
    """
    Build prompt with job's CSV/transactions and user message; return LLM reply.
    job_data: { "transactions": [...], "csv_content": "..." }
    """
    csv_content = job_data.get("csv_content", "")
    if not csv_content:
        csv_content = "No transaction data available."

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a helpful assistant that explains and validates bank statement data. "
                "Answer ONLY based on the CSV/transaction data provided. "
                "Justify categories and data when asked (e.g. why a row was categorized as X). "
                "Be concise and accurate.",
            ),
            (
                "human",
                "Statement data (CSV):\n{csv_content}\n\nUser question: {message}",
            ),
        ]
    )
    chain = prompt | _get_llm() | StrOutputParser()
    return chain.invoke({"csv_content": csv_content[:15000], "message": message})
