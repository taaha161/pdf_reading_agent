# Deploying the PDF Bank Statement Processor

Deploy the **backend** (FastAPI) and **frontend** (React) so you can share a single link with your client. The frontend calls the backend API; both need to be deployed and the frontend must know the backend URL.

---

## Option A: Render (Backend) + Vercel (Frontend) — recommended

Free tiers for both. Backend runs in Docker with OCR support (poppler, tesseract).

### 1. Deploy the backend to Render

1. Push your code to a **GitHub** repository (if you haven’t already).

2. Go to [render.com](https://render.com) and sign in (e.g. with GitHub).

3. **New → Web Service**.

4. Connect the repo and set:
   - **Root Directory**: `backend`
   - **Environment**: **Docker**
   - **Name**: e.g. `pdf-statement-api`

5. **Environment variables** (Add in Render dashboard):
   - `GOOGLE_GEMINI_API_KEY` = your Google Gemini API key (required for AI extraction, categorization, chat, and scanned-PDF vision)
   - `SUPABASE_URL` = your Supabase project URL (Project Settings → API)
   - `DATABASE_URL` = Supabase connection string (Project Settings → Database; use pooler for serverless, port 6543)
   - `ALLOWED_ORIGINS` = your frontend URL (see step 2 below). After deploying the frontend, set this to e.g. `https://bankstatementscanner.com` (no trailing slash). You can add multiple origins separated by commas.

6. Deploy. Note the backend URL, e.g. `https://pdf-statement-api.onrender.com`.

**Note:** On the free tier the service may sleep after inactivity; the first request after that can take 30–60 seconds.

### 2. Deploy the frontend to Vercel

1. Go to [vercel.com](https://vercel.com) and sign in (e.g. with GitHub).

2. **Add New → Project** and import the same repo.

3. Configure:
   - **Root Directory**: `frontend`
   - **Framework Preset**: Vite
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`

4. **Environment variables** (add in Vercel):
   - `VITE_API_URL` = your **backend URL** from step 1, e.g. `https://pdf-statement-api.onrender.com` (no trailing slash)
   - `VITE_SUPABASE_URL` = your Supabase project URL (same as backend)
   - `VITE_SUPABASE_PUBLISHABLE_KEY` = Supabase **Publishable key** (`sb_publishable_...`) from Project Settings → API Keys (not Legacy)

5. Deploy. Vercel will give you a URL (e.g. `https://bankstatementscanner.com` if using a custom domain).

### 3. Point backend at the frontend

1. In **Render** → your Web Service → **Environment**:
   - Set `ALLOWED_ORIGINS` to your frontend URL, e.g. `https://bankstatementscanner.com`
   - (Add `http://localhost:5173` too if you want to test locally against the deployed API.)

2. Redeploy the backend if you changed env vars so CORS uses the new origin.

Share the **Vercel URL** with your client. They open that link and use the app; the frontend talks to the backend automatically.

---

## Option D: GitHub Pages (Frontend only)

The backend must be hosted elsewhere (e.g. Render). In the repo: **Settings → Pages**, set **Source** to **GitHub Actions**. Add a repository secret `VITE_API_URL` (backend URL). Set backend `ALLOWED_ORIGINS` to your GitHub Pages URL (e.g. `https://USERNAME.github.io/REPO_NAME/`). Push to trigger the deploy workflow; see `.github/workflows/deploy-pages.yml` if present.

---

## Option B: Railway (Backend + Frontend)

[Railway](https://railway.app) can host both the API and the frontend.

1. Push code to GitHub and connect the repo in Railway.

2. **Backend**
   - New Service from repo, **Root Directory** = `backend`.
   - Use **Dockerfile** (Railway will detect `backend/Dockerfile` if you set root to `backend`).
   - Add env: `GOOGLE_GEMINI_API_KEY`, `ALLOWED_ORIGINS` = your frontend URL (you can set after deploying frontend).

3. **Frontend**
   - New Service from same repo, **Root Directory** = `frontend`.
   - Build: `npm run build`, Output: `dist`. Use a static server (e.g. `npx serve dist` or Railway’s static site support).
   - Add env: `VITE_API_URL` = Railway backend URL.

4. Set `ALLOWED_ORIGINS` on the backend to the Railway frontend URL.

---

## Option C: Single server (backend serves frontend)

If you prefer one URL and one deployment:

1. Build the frontend locally with the backend URL:
   ```bash
   cd frontend
   echo "VITE_API_URL=https://your-backend-url.com" > .env.production
   npm run build
   ```
2. Copy `frontend/dist` into the backend (e.g. `backend/static`) and configure FastAPI to serve those static files and fallback to `index.html` for SPA routing. Then deploy only the backend (e.g. Render with Docker). Your client uses the single backend URL.

---

## Checklist before sharing with client

- [ ] **GOOGLE_GEMINI_API_KEY** set on the backend (required for extraction, categorization, chat, and scanned-PDF vision). If unset, Ollama is used for text/chat where available; vision is skipped.
- [ ] **ALLOWED_ORIGINS** on the backend includes the exact frontend URL (no trailing slash).
- [ ] **VITE_API_URL** on the frontend build is the backend URL (no trailing slash).
- [ ] If using Render free tier, tell the client the first load after idle may be slow (wake-up).

---

## Env reference

| Variable          | Where     | Purpose |
|-------------------|-----------|--------|
| `GOOGLE_GEMINI_API_KEY` | Backend   | Google Gemini API key for extraction, categorization, chat, and scanned-PDF vision. If unset, Ollama is used for text/chat. |
| `SUPABASE_URL`    | Backend   | Supabase project URL for JWT verification (JWKS). |
| `DATABASE_URL`    | Backend   | Supabase database connection string (use pooler for serverless). |
| `ALLOWED_ORIGINS` | Backend   | Comma-separated frontend origins for CORS, e.g. `https://bankstatementscanner.com`. |
| `VITE_API_URL`    | Frontend  | Backend API URL. Set at **build** time. |
| `VITE_SUPABASE_URL` | Frontend | Supabase project URL (same as backend). |
| `VITE_SUPABASE_PUBLISHABLE_KEY` | Frontend | Supabase Publishable key (`sb_publishable_...`). |
| `PORT`            | Backend   | Set by Render/Railway; no need to set yourself. |
