# Deploy to GitHub Pages

The **frontend** is deployed to GitHub Pages. The **backend** (FastAPI) cannot run on GitHub Pages and must be hosted elsewhere (e.g. Render). The frontend will call your backend URL.

---

## 1. Deploy the backend first

Deploy the API to a host that runs Python/Docker (e.g. [Render](https://render.com)):

- **Render**: New → Web Service, connect your repo, **Root Directory** = `backend`, **Environment** = Docker. Add env vars: `GROQ_API_KEY`, and later `ALLOWED_ORIGINS` (your GitHub Pages URL).
- See [DEPLOY.md](../DEPLOY.md) for full backend steps.

Note the backend URL, e.g. `https://pdf-statement-api.onrender.com`.

---

## 2. Enable GitHub Pages with Actions

1. In your repo on GitHub: **Settings → Pages**.
2. Under **Build and deployment**, set **Source** to **GitHub Actions**.

---

## 3. Add the backend URL as a secret

1. **Settings → Secrets and variables → Actions**.
2. **New repository secret**:
   - **Name**: `VITE_API_URL`
   - **Value**: your backend URL (e.g. `https://pdf-statement-api.onrender.com`) — no trailing slash.

The workflow uses this when building the frontend so the app knows where to send API requests.

---

## 4. Allow the frontend origin on the backend (CORS)

On your backend host (e.g. Render), set:

- **`ALLOWED_ORIGINS`** = your GitHub Pages URL, e.g. `https://YOUR_USERNAME.github.io` (no trailing slash).

For a **project site** (repo name in path), the URL is:

`https://YOUR_USERNAME.github.io/YOUR_REPO_NAME/`

Use that full URL as `ALLOWED_ORIGINS` (one value, or comma-separated if you have several).

---

## 5. Deploy the frontend

Push to the `main` branch (or run the workflow manually from the **Actions** tab):

```bash
git add .
git commit -m "Deploy to GitHub Pages"
git push origin main
```

The **Deploy to GitHub Pages** workflow will:

1. Build the frontend with `VITE_BASE_PATH=/<repo-name>/` and `VITE_API_URL=<your backend>`.
2. Deploy the built files to GitHub Pages.

After it finishes, your app is at:

- **Project site**: `https://YOUR_USERNAME.github.io/YOUR_REPO_NAME/`
- **User/org site** (if you use that): `https://YOUR_USERNAME.github.io/`

Share that link with your client.

---

## Checklist

- [ ] Backend deployed and URL noted
- [ ] Repo secret `VITE_API_URL` set to backend URL
- [ ] Pages → Source set to **GitHub Actions**
- [ ] Backend `ALLOWED_ORIGINS` includes your GitHub Pages URL
- [ ] Push to `main` (or run the workflow) to deploy

---

## Local build (same as GitHub Pages)

To build the frontend the same way as on GitHub Pages (e.g. to test):

```bash
cd frontend
VITE_BASE_PATH=/pdf_reading_agent/ VITE_API_URL=https://your-backend.onrender.com npm run build
```

Use your actual repo name and backend URL. Then open `frontend/dist/index.html` or serve `frontend/dist` with a static server.
