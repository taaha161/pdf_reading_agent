# PDF Bank Statement Processor MVP

Upload bank statement PDFs (digital or scanned), get itemized and categorized transactions as CSV, and validate results with a chatbot.

## Stack

- **Backend**: Python 3.11+, FastAPI, LangChain (Groq or Ollama), pdfplumber, pdf2image, pytesseract
- **Frontend**: React, Vite

## Setup

### Backend

1. Create a virtualenv and install dependencies:

   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate   # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **LLM**: Use either Groq (free tier) or Ollama (local).
   - **Groq**: Get an API key from [console.groq.com](https://console.groq.com), then set `GROQ_API_KEY` in your environment or a `.env` file (see `backend/.env.example`).
   - **Ollama**: Install [Ollama](https://ollama.ai) and run `ollama pull llama3.2`. No API key needed; the app will use Ollama if `GROQ_API_KEY` is not set.

3. **OCR (for scanned PDFs)**:
   - **Tesseract**: Install [Tesseract](https://github.com/tesseract-ocr/tesseract) and ensure it’s on your PATH.
   - **pdf2image**: Requires Poppler. On macOS: `brew install poppler`. On Ubuntu: `sudo apt install poppler-utils`.

4. Load env (optional): `pip install python-dotenv` and load `.env` in `main.py`, or export variables manually.

5. Run the API:

   ```bash
   uvicorn main:app --reload
   ```

   API runs at `http://localhost:8000`.

### Frontend

1. Install and run:

   ```bash
   cd frontend
   npm install
   npm run dev
   ```

2. The app will use `http://localhost:8000` as the API URL by default. To override, set `VITE_API_URL` in a `.env` file (e.g. `VITE_API_URL=http://localhost:8000`).

3. Open the URL shown in the terminal (usually `http://localhost:5173`).

## Usage

1. Upload a bank statement PDF (drag-and-drop or click to choose).
2. Wait for processing; the table will show extracted transactions with categories.
3. Use **Download CSV** to save the data.
4. In **Validate CSV**, ask questions like “Why is Amazon in Shopping?” to get explanations based on the generated data.

## API

- `POST /api/process-pdf` — multipart `file` (PDF). Returns `job_id`, `transactions`, `csv_url`.
- `GET /api/jobs/{job_id}/csv` — download CSV for a job.
- `POST /api/chat` — body: `{ "job_id": "...", "message": "..." }`. Returns `{ "reply": "..." }`.

## Environment

See `backend/.env.example`. Main variable: `GROQ_API_KEY` (optional; if unset, Ollama is used).

## Deploy (Backend + Frontend)

**Step-by-step:** see [docs/DEPLOY_STEPS.md](docs/DEPLOY_STEPS.md) to host the backend on **Render** and the frontend on **Vercel** (free tiers). You’ll get a single link to share with your client.
