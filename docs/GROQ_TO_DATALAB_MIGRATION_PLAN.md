# Migrate from Groq to Datalab

## Overview

Migrate from Groq (and optional Ollama fallback) to **Datalab for PDF-to-text only**. Keep **AI (Groq/Ollama) for text→transactions, categorization, and chat**, since Datalab does not expose a chat API and does not automatically categorize transactions from description/details.

---

## Clarification: current stack

The codebase uses **Groq** (Groq API with Llama models), not xAI Grok. Migration is **Groq → Datalab** for the **PDF→text** flow only. [Datalab](https://documentation.datalab.to/) provides document conversion (and structured extraction) with an integrated LLM; it does **not** expose a generic chat/completions API. Datalab’s Extract API fills schema fields from the document but is **not** documented to infer transaction categories from description text (e.g. “Walmart” → Groceries). Your existing `CATEGORY_GUIDANCE` in `statement_agent` is the right place for that logic, so we keep AI for extraction + categorization.

---

## Current usage (3 places)

| Location | Purpose | After migration |
|----------|---------|-----------------|
| [backend/services/pdf_processor.py](backend/services/pdf_processor.py) | PDF → text (direct + OCR + vision for scanned pages) | **Datalab Convert** when `DATALAB_API_KEY` set; else unchanged |
| [backend/services/statement_agent.py](backend/services/statement_agent.py) | Extract transactions from text + categorize | **Unchanged** — keep Groq/Ollama |
| [backend/services/chat_service.py](backend/services/chat_service.py) | Q&A about job CSV/transactions | **Unchanged** — keep Groq/Ollama |

Pipeline in [backend/main.py](backend/main.py): `extract_text_from_pdf` → `extract_and_categorize` → store job; chat uses `get_reply` with job data.

---

## Datalab API (used only for Convert)

- **Base URL**: `https://www.datalab.to`
- **Auth**: Header `X-API-Key` ([API reference](https://documentation.datalab.to/api-reference/health))
- **Convert** (`POST /api/v1/convert`): PDF/image → markdown, HTML, or JSON. Async: returns `request_id` and `request_check_url`; poll `GET /api/v1/convert/{request_id}` until `status == "complete"`, then read `markdown` (or `html`/`json`).
- **Extract** and chat: **Not used** in this migration. Transaction extraction and categorization stay with Groq/Ollama.

---

## Target architecture

```
Current:  PDF → [pdfplumber/OCR/Groq vision] → raw text → [ChatGroq] extract + categorize → transactions
                                                                     → chat (ChatGroq)

After:    PDF → [Datalab Convert] → markdown → [ChatGroq/Ollama] extract + categorize → transactions  (unchanged)
                                                      → chat (unchanged)
```

When `DATALAB_API_KEY` is set, only the **PDF → text** step is replaced by Datalab; the rest of the pipeline is unchanged.

---

## Implementation plan

### 1. Datalab client module

- Add **`backend/services/datalab_client.py`**:
  - **`convert_pdf_to_markdown(file_content: bytes, filename: str) -> str`**
    - POST file to `https://www.datalab.to/api/v1/convert` (multipart: `file`, `output_format=markdown`).
    - Use header `X-API-Key` from env `DATALAB_API_KEY`.
    - Poll `GET /api/v1/convert/{request_id}` with backoff until `status == "complete"`.
    - Return the `markdown` field from the response; handle errors and timeouts.
- Use `httpx` for HTTP (async or sync to match the rest of the app). Add `httpx` to [backend/requirements.txt](backend/requirements.txt) if needed.

### 2. PDF processing path

- In [backend/services/pdf_processor.py](backend/services/pdf_processor.py):
  - When `DATALAB_API_KEY` is set: call `datalab_client.convert_pdf_to_markdown(content, filename)` and return its result. No direct text extraction, OCR, or Groq vision in that branch.
  - When not set: keep current behavior (direct text → OCR/vision as today) so the app works without Datalab.
- In [backend/main.py](backend/main.py): no change; keep calling `extract_text_from_pdf` then `extract_and_categorize`.

### 3. Transaction extraction and categorization

- **No changes** to [backend/services/statement_agent.py](backend/services/statement_agent.py).
- Continue using **Groq (or Ollama)** for:
  - Extracting transactions from text (JSON array).
  - Categorizing each transaction using `CATEGORY_GUIDANCE` and description/details.
- Datalab is **not** used for Extract; we do not rely on it for categorization.

### 4. Chat

- **No changes** to [backend/services/chat_service.py](backend/services/chat_service.py).
- Continue using Groq or Ollama for `get_reply`.

### 5. Config and dependencies

- **Env**: Document `DATALAB_API_KEY`. Optionally `DATALAB_BASE_URL` (default `https://www.datalab.to`). Keep `GROQ_API_KEY` for extraction, categorization, and chat.
- **Requirements**: Add `httpx`. Keep `groq` and `langchain-groq` for statement_agent and chat.
- **Health** (optional): Call Datalab `GET /api/v1/health` when `DATALAB_API_KEY` is set to verify connectivity.

### 6. Testing and rollout

- With `DATALAB_API_KEY` set: test digital and scanned PDFs; Datalab Convert should supply markdown; extraction and categorization should behave as today.
- With key unset: behavior unchanged (current PDF path + Groq/Ollama).

---

## Summary

| Component | Before | After |
|-----------|--------|--------|
| PDF → text | pdfplumber/pypdf, OCR, Groq vision | **Datalab Convert** (when key set); else unchanged |
| Text → transactions + categorization | ChatGroq / Ollama | **Unchanged** (Groq / Ollama) |
| Chat (Q&A) | ChatGroq / Ollama | **Unchanged** (Groq / Ollama) |

No frontend changes. Backend: new Datalab client for PDF→markdown only, conditional use in `pdf_processor`, env var `DATALAB_API_KEY`, and optional health check.
