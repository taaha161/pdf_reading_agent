# PDF Bank Statement Processor — Frontend

React + Vite frontend for the PDF Bank Statement Processor. Upload bank statement PDFs, view itemized transactions, download CSV, and validate results with a chatbot.

## Setup

```bash
npm install
npm run dev
```

Set `VITE_API_URL` in `.env` to the backend API (default `http://localhost:8000`). For auth, set `VITE_SUPABASE_URL` and `VITE_SUPABASE_PUBLISHABLE_KEY` (see root [README](../README.md)).

## Build

```bash
npm run build
```

Output is in `dist/`. For production, set `VITE_API_URL` (and Supabase vars) before building.
