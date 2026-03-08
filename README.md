# PDF Bank Statement Processor MVP

Upload bank statement PDFs (digital or scanned), get itemized and categorized transactions as CSV, and validate results with a chatbot.

## Stack

- **Backend**: Python 3.11+, FastAPI, LangChain (Gemini or Ollama), pdfplumber, pdf2image, pytesseract
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

2. **LLM**: Use either Google Gemini or Ollama (local).
   - **Gemini**: Get an API key from [Google AI Studio](https://ai.google.dev/gemini-api/docs/api-key), then set `GOOGLE_GEMINI_API_KEY` in your environment or a `.env` file (see `backend/.env.example`).
   - **Ollama**: Install [Ollama](https://ollama.ai) and run `ollama pull llama3.2`. No API key needed; the app will use Ollama if `GOOGLE_GEMINI_API_KEY` is not set.

3. **OCR (for scanned PDFs)**:
   - **Tesseract**: Install [Tesseract](https://github.com/tesseract-ocr/tesseract) and ensure it’s on your PATH.
   - **pdf2image**: Requires Poppler. On macOS: `brew install poppler`. On Ubuntu: `sudo apt install poppler-utils`.

4. Load env (optional): `pip install python-dotenv` and load `.env` in `main.py`, or export variables manually.

5. **Redis (optional)** — For shared rate limiting across multiple backend instances (e.g. production), set `REDIS_URL` in `.env`. See [Redis setup](#redis-setup) below.

6. Run the API:

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

- **Backend:** See `backend/.env.example`. Main: `GOOGLE_GEMINI_API_KEY` (optional); for auth: `SUPABASE_URL`, `DATABASE_URL` (JWT verification uses JWKS; no legacy API keys).
- **Frontend:** See `frontend/.env.example`. `VITE_API_URL`; for auth: `VITE_SUPABASE_URL`, `VITE_SUPABASE_PUBLISHABLE_KEY` (new Publishable key from Supabase; legacy anon key is deprecated).

## Auth (Supabase)

The app uses Supabase for sign-in (social, email, phone). Create a project at [supabase.com](https://supabase.com), enable Email and Phone auth and OAuth providers (e.g. Google). Use the **new API keys**: in Project Settings → API Keys, copy the **Publishable key** (`sb_publishable_...`) for the frontend (do not use Legacy API Keys). Set the env vars above and run the SQL migrations in `supabase/migrations/` in the Supabase SQL Editor (or via Supabase CLI) to create `jobs`, `profiles`, and `subscription` tables.

**Next steps:** See [docs/NEXT_STEPS.md](docs/NEXT_STEPS.md) for setup, running migrations, optional features (My jobs, profiles, Stripe), and deployment.

## Redis setup

Redis is used only for **rate-limit storage** when `REDIS_URL` is set. Single-instance or local dev can skip it (in-memory limits are used).

### Local (macOS / Linux)

**Option A — Homebrew (macOS):**
```bash
brew install redis
brew services start redis   # start on login, or:
redis-server                 # run in foreground
```
Default: `redis://localhost:6379`. In `backend/.env` add:
```bash
REDIS_URL=redis://localhost:6379/0
```

**Option B — Docker:**
```bash
docker run -d --name redis -p 6379:6379 redis:7-alpine
```
Then set `REDIS_URL=redis://localhost:6379/0` in `backend/.env`.

**Option C — Ubuntu/Debian:**
```bash
sudo apt update && sudo apt install redis-server
sudo systemctl start redis-server
```
Use `REDIS_URL=redis://localhost:6379/0`.

### Production (hosted)

Use a managed Redis service and set `REDIS_URL` in your deployment env:

- **Upstash** — [upstash.com](https://upstash.com) (serverless, free tier): create a Redis DB and copy the REST or Redis URL.
- **Redis Cloud** — [redis.com/try-free](https://redis.com/try-free)
- **Railway / Render / Fly.io** — add a Redis add-on and use the provided URL.

URL format: `redis://[user:password@]host:port[/db]`. Example with password:
```bash
REDIS_URL=redis://:yourpassword@your-host.redis.cloud:12345/0
```

### Verify

With the backend running and `REDIS_URL` set, rate limits are shared across instances. To confirm Redis is used, start Redis, set `REDIS_URL`, restart the API, and hit a rate-limited endpoint until you get 429; the limit will persist across API restarts.

## Deploy (Backend + Frontend)

**Step-by-step:** see [docs/DEPLOY_STEPS.md](docs/DEPLOY_STEPS.md) to host the backend on **Render** and the frontend on **Vercel** (free tiers). You’ll get a single link to share with your client.
