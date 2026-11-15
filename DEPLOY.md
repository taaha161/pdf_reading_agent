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
| `RESEND_API_KEY`  | Backend   | Resend API key for owner notifications (signup/login/scan). Blank disables all notifications. |
| `SENTRY_DSN`      | Backend   | Sentry DSN for backend error monitoring. Blank disables it. |
| `VITE_SENTRY_DSN` | Frontend (build) | Sentry DSN for frontend error monitoring. Read at build time; blank disables it. |
| `SENTRY_AUTH_TOKEN`, `SENTRY_ORG`, `SENTRY_PROJECT` | Frontend (build) | Optional: upload source maps to Sentry during the Vercel build (deleted from `dist` afterwards). |
| `NOTIFY_EMAIL_TO` | Backend   | Notification recipient. Default `team@bankstatementscanner.com`. |
| `NOTIFY_EMAIL_FROM` | Backend | Verified Resend sender. Default `BankStatementScanner <notifications@bankstatementscanner.com>`. |
| `NOTIFY_WEBHOOK_SECRET` | Backend | Shared secret for the Supabase signup webhook (`X-Webhook-Secret` header). Blank disables signup emails. |
| `PORT`            | Backend   | Set by Render/Railway; no need to set yourself. |

---

## Owner notifications (email on signup / login / scan)

An email goes to `NOTIFY_EMAIL_TO` on each event. All sends are best-effort — they never block or fail a user request.

1. **Resend**: create an account at [resend.com](https://resend.com), verify the sending domain (`bankstatementscanner.com`), and set `RESEND_API_KEY` on the backend. Set `NOTIFY_EMAIL_FROM` to an address on the verified domain.
2. **Scan** emails work immediately — fired server-side from `POST /api/process-pdf`.
3. **Login** emails: the frontend calls `POST /api/events/login` on a real sign-in (deduped per browser session). No config beyond `RESEND_API_KEY`.
4. **Signup** emails: set `NOTIFY_WEBHOOK_SECRET` on the backend, then in Supabase → **Database → Webhooks** create a webhook:
   - Table: `auth.users`, Events: **Insert**
   - Type: **HTTP Request**, Method: `POST`, URL: `https://<backend-url>/api/hooks/user-created`
   - HTTP Header: `X-Webhook-Secret: <same value as NOTIFY_WEBHOOK_SECRET>`

## Affiliate program

Affiliates are set up by us through admin endpoints guarded by `API_AUTH_SECRET`
(same secret as `/admin/generate-blog`). Run `supabase/migrations/20261116000000_affiliates.sql` first.

How it works:

- Each affiliate gets a unique code (3–32 chars: a–z, 0–9, `-`, `_`) and their own `revenue_share_pct`.
- A user signs up with the code by opening `https://bankstatementscanner.com/?ref=<code>` (any page;
  kept 30 days) or typing it into **Referral code** on the signup form.
- On the new account's first sign-in the app calls `POST /api/referral/claim`. Only accounts under 7 days
  old can claim, once, so existing users can't be attached to an affiliate later.
- Every payment by that user (subscription invoices, page packs) records a commission:
  pre-tax amount paid × the affiliate's percentage **at that moment**. Free/trial ($0) invoices record nothing.
  Changing an affiliate's percentage only affects future payments.
- `commission_months` limits how long after signup payments earn commission (omit for lifetime).
- Payouts are manual: pay the affiliate, then mark their pending commissions paid.
- Optional **user discount** per affiliate (`discount_pct`, default 0 = none):
  - Monthly plan: `discount_pct` off for `discount_months` from when they subscribe (omit = forever), first
    subscription only. Applied as a Stripe coupon the backend creates automatically and reuses.
  - Page packs (`discount_packs: true`): same % off while within `discount_months` of signup. Never below $0.50.
  - The signup form shows the discount as soon as a valid code is entered; the Account page shows discounted prices.
  - Discounted checkouts hide Stripe's promo-code box (Stripe allows one or the other).
  - Commission is on what the user actually paid, so it's after the discount.
  - Changing the discount affects new subscriptions only; existing subscribers keep the coupon they got.
- Not automated: refunds/chargebacks. Void a commission by hand
  (`UPDATE affiliate_commissions SET status = 'void' WHERE source_id = '<stripe id>'`).

```bash
API=https://<backend-host>; AUTH="Authorization: Bearer $API_AUTH_SECRET"

# Create an affiliate: 20% of everything their referrals pay, for 12 months
curl -X POST $API/admin/affiliates -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"name":"Jane Doe","email":"jane@example.com","code":"jane","revenue_share_pct":20,"commission_months":12}'

# ...and give their referrals 25% off the plan for 3 months, plus 25% off page packs in that window
curl -X POST $API/admin/affiliates -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"name":"Sam Lee","code":"sam","revenue_share_pct":20,"discount_pct":25,"discount_months":3,"discount_packs":true}'

# Add or change a discount later
curl -X PATCH $API/admin/affiliates/<id> -H "$AUTH" -H 'Content-Type: application/json' -d '{"discount_pct":10,"discount_months":1}'

# List affiliates with referrals, referred revenue, pending/paid commission (cents)
curl $API/admin/affiliates -H "$AUTH"

# Change terms / deactivate (inactive codes can't be claimed and earn nothing new)
curl -X PATCH $API/admin/affiliates/<id> -H "$AUTH" -H 'Content-Type: application/json' -d '{"revenue_share_pct":25}'
curl -X PATCH $API/admin/affiliates/<id> -H "$AUTH" -H 'Content-Type: application/json' -d '{"active":false}'

# Commission ledger, then record a payout (marks all pending up to now as paid)
curl "$API/admin/affiliates/<id>/commissions?status=pending" -H "$AUTH"
curl -X POST $API/admin/affiliates/<id>/payouts -H "$AUTH" -H 'Content-Type: application/json' -d '{}'
```
