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
   - `GROQ_API_KEY` = your Groq API key (required for AI and vision)
   - `ALLOWED_ORIGINS` = your frontend URL (see step 2 below). After deploying the frontend, set this to e.g. `https://your-app.vercel.app` (no trailing slash). You can add multiple origins separated by commas.

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

5. Deploy. Vercel will give you a URL like `https://your-project.vercel.app`.

### 3. Point backend at the frontend

1. In **Render** → your Web Service → **Environment**:
   - Set `ALLOWED_ORIGINS` to your Vercel URL, e.g. `https://your-project.vercel.app`
   - (Add `http://localhost:5173` too if you want to test locally against the deployed API.)

2. Redeploy the backend if you changed env vars so CORS uses the new origin.

Share the **Vercel URL** with your client. They open that link and use the app; the frontend talks to the backend automatically.

---

## Option B: Railway (Backend + Frontend)

[Railway](https://railway.app) can host both the API and the frontend.

1. Push code to GitHub and connect the repo in Railway.

2. **Backend**
   - New Service from repo, **Root Directory** = `backend`.
   - Use **Dockerfile** (Railway will detect `backend/Dockerfile` if you set root to `backend`).
   - Add env: `GROQ_API_KEY`, `ALLOWED_ORIGINS` = your frontend URL (you can set after deploying frontend).

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

- [ ] **GROQ_API_KEY** set on the backend (required for extraction and chat).
- [ ] **ALLOWED_ORIGINS** on the backend includes the exact frontend URL (no trailing slash).
- [ ] **VITE_API_URL** on the frontend build is the backend URL (no trailing slash).
- [ ] If using Render free tier, tell the client the first load after idle may be slow (wake-up).

---

## Env reference

| Variable          | Where     | Purpose |
|-------------------|-----------|--------|
| `GROQ_API_KEY`    | Backend   | Groq API key for LLM and vision. |
| `ALLOWED_ORIGINS` | Backend   | Comma-separated frontend origins for CORS, e.g. `https://app.vercel.app`. |
| `VITE_API_URL`    | Frontend  | Backend API URL, e.g. `https://api.render.com`. Set at **build** time. |
| `PORT`            | Backend   | Set by Render/Railway; no need to set yourself. |
