# Steps to Deploy Backend + Frontend

Use **Render** for the backend (FastAPI + OCR) and **Vercel** for the frontend (React). Both have free tiers.

---

## Prerequisites

- Code pushed to a **GitHub** repository
- A **Groq** API key from [console.groq.com](https://console.groq.com) (for AI and vision)

---

## Part 1: Backend on Render

1. **Open Render**  
   Go to [render.com](https://render.com) and sign in with GitHub.

2. **Create a Web Service**  
   Click **New +** → **Web Service**.

3. **Connect the repo**  
   Select your GitHub account and the `pdf_reading_agent` repo (or whatever you named it). Click **Connect**.

4. **Configure the service**
   - **Name**: e.g. `pdf-statement-api` (this becomes part of the URL)
   - **Region**: choose one close to you or your client
   - **Root Directory**: click **Add root directory** and enter `backend`
   - **Environment**: select **Docker**
   - **Instance Type**: leave **Free** (or pick a paid plan for no sleep)

5. **Add environment variables**  
   In **Environment Variables** → **Add Environment Variable**:
   - **Key**: `GROQ_API_KEY`  
     **Value**: paste your Groq API key  
   - **Key**: `ALLOWED_ORIGINS`  
     **Value**: leave empty for now (you’ll set it after deploying the frontend)

6. **Deploy**  
   Click **Create Web Service**. Render will build and deploy. Wait until the status is **Live**.

7. **Copy the backend URL**  
   At the top you’ll see something like `https://pdf-statement-api.onrender.com`. Copy this URL (no trailing slash). You’ll use it for the frontend and for CORS.

---

## Part 2: Frontend on Vercel

1. **Open Vercel**  
   Go to [vercel.com](https://vercel.com) and sign in with GitHub.

2. **Import the project**  
   Click **Add New…** → **Project**. Select the same GitHub repo and click **Import**.

3. **Configure the project**
   - **Root Directory**: click **Edit** and set to `frontend`
   - **Framework Preset**: should detect **Vite**
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`

4. **Add environment variable**  
   Under **Environment Variables**:
   - **Key**: `VITE_API_URL`
   - **Value**: the **backend URL** from Part 1 (e.g. `https://pdf-statement-api.onrender.com`) — no trailing slash
   - **Environment**: leave all (Production, Preview, Development) checked

5. **Deploy**  
   Click **Deploy**. Wait until the deployment finishes.

6. **Copy the frontend URL**  
   You’ll see a URL like `https://pdf-statement-api-xxxx.vercel.app`. Copy it (no trailing slash). This is the link you’ll share with your client.

---

## Part 3: Connect backend to frontend (CORS)

1. **Go back to Render**  
   Open your Web Service (e.g. `pdf-statement-api`).

2. **Set CORS**  
   Open **Environment** (left sidebar). Find `ALLOWED_ORIGINS` and set its value to your **Vercel frontend URL** from Part 2, e.g.:
   ```text
   https://pdf-statement-api-xxxx.vercel.app
   ```
   If you use a custom domain on Vercel, add that too. You can add multiple origins separated by commas, e.g.:
   ```text
   https://your-app.vercel.app,https://your-custom-domain.com
   ```
   Save.

3. **Redeploy the backend**  
   In Render, open **Manual Deploy** → **Deploy latest commit** so the new `ALLOWED_ORIGINS` is applied.

---

## Done

- **Frontend (share this with your client)**: your Vercel URL, e.g. `https://your-app.vercel.app`
- **Backend**: your Render URL (used by the frontend automatically; no need to share)

### Quick checklist

- [ ] Backend on Render is **Live** and you have its URL
- [ ] `GROQ_API_KEY` set on Render
- [ ] Frontend on Vercel deployed with `VITE_API_URL` = backend URL
- [ ] `ALLOWED_ORIGINS` on Render = Vercel URL (and redeployed)

### Notes

- **Render free tier**: the backend may sleep after ~15 minutes of no use. The first request after that can take 30–60 seconds (cold start).
- **Vercel**: the frontend is static; no cold starts. If you change `VITE_API_URL`, redeploy the frontend so the new value is baked into the build.
