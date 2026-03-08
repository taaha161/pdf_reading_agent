# PDF Bank Statement Processor

Upload bank statement PDFs (digital or scanned), get itemized and categorized transactions as CSV, and validate results with a chatbot.

**Stack:** Backend — Python, FastAPI, LangChain (Gemini or Ollama), pdfplumber, OCR. Frontend — React, Vite.

---

## How to run

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open the URL shown (usually `http://localhost:5173`). It uses `http://localhost:8000` as the API by default; set `VITE_API_URL` in `.env` to override. See `frontend/.env.example` for auth (Supabase) vars.
