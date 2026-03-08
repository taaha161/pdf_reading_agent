# Next Steps (Auth + Database)

This document covers what to do after the auth and database implementation: get auth running locally, run migrations, optional features, and deployment.

---

## 1. Get auth running locally

### 1.1 Create a Supabase project

1. Go to [supabase.com](https://supabase.com) and create a project.
2. In **Authentication → Providers**, enable:
   - **Email** (and optionally “Confirm email”).
   - **Phone** (SMS may need Supabase Pro or Twilio for production).
   - **Google** (or other OAuth): add your OAuth client ID/secret in the provider settings.
3. In **Authentication → URL Configuration**, add your redirect URLs, e.g.:
   - `http://localhost:5173`
   - Your production frontend URL (e.g. `https://your-app.vercel.app`).

### 1.2 Run the database migration

1. In the Supabase dashboard, open **SQL Editor**.
2. Copy the contents of [supabase/migrations/20250307000001_create_jobs_profiles_subscription.sql](../supabase/migrations/20250307000001_create_jobs_profiles_subscription.sql).
3. Paste and run the SQL. This creates `jobs`, `profiles`, and `subscription` and their RLS policies.

Alternatively, if you use the Supabase CLI: `supabase db push` (from the project root with Supabase linked).

### 1.3 Set environment variables

**Backend** (e.g. `backend/.env`):

- `SUPABASE_URL` — Project Settings → API → Project URL (required for auth). The backend uses **JWKS** (`{SUPABASE_URL}/auth/v1/.well-known/jwks.json`) to verify tokens with Supabase’s new JWT signing keys (RS256/ES256). No legacy JWT secret needed.
- `DATABASE_URL` — Project Settings → Database → Connection string (use the **Connection pooling** URI for serverless; port 6543).

**Frontend** (e.g. `frontend/.env`):

- `VITE_SUPABASE_URL` — same as backend `SUPABASE_URL`
- `VITE_SUPABASE_PUBLISHABLE_KEY` — Project Settings → **API Keys** → Publishable key (`sb_publishable_...`). Do not use Legacy API Keys (anon) if they are disabled.  

See [backend/.env.example](../backend/.env.example) and [frontend/.env.example](../frontend/.env.example) for the full list.

### 1.4 Run and test

1. Start backend: `cd backend && uvicorn main:app --reload`
2. Start frontend: `cd frontend && npm run dev`
3. Open the app; go to **Log in** or **Sign up**.
4. Try **Continue with Google** (after configuring Google OAuth in Supabase), **email + password**, or **phone OTP** (if SMS is configured).
5. After signing in, you should be redirected to `/scanner`. Upload a PDF and confirm a job is created and CSV/chat work.
6. Confirm unauthenticated requests are rejected: open DevTools → clear cookies / sign out, then call the API without a token; you should get 401.

---

## 2. Deployment checklist

Before going to production:

- [ ] Supabase project has production redirect URLs and allowed origins set.
- [ ] Backend env on Render (or your host): `SUPABASE_URL`, `DATABASE_URL`, `ALLOWED_ORIGINS` (include your frontend URL). JWT verification uses JWKS (no legacy keys).
- [ ] Frontend env at build time: `VITE_API_URL`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_PUBLISHABLE_KEY`.
- [ ] Migration has been run on the Supabase project used in production.
- [ ] CORS: frontend origin is in backend `ALLOWED_ORIGINS` and in Supabase Auth URL configuration.

See [DEPLOY_STEPS.md](DEPLOY_STEPS.md) for full deploy instructions.

---

## 3. Optional enhancements

### 3.1 “My jobs” list

- Add **backend**: `GET /api/jobs` that returns the current user’s jobs (from `jobs` filtered by `user_id`, ordered by `created_at DESC`).
- Add **frontend**: a “My jobs” page or section that calls this endpoint and lets users reopen a past job (e.g. navigate to `/scanner?job_id=...` and load that job’s data).

### 3.2 Profiles sync

- On first login (or signup), create or update a row in `profiles`: set `id` = auth user id, and sync `email`, `phone`, `display_name` from Supabase Auth (e.g. via a Supabase Auth hook or a backend endpoint that the frontend calls after login).
- Optionally link Stripe customer id to `profiles.stripe_id` when you add billing.

### 3.3 Stripe (subscription tier)

- When you integrate Stripe, create/update a row in `subscription` per user: `user_id`, `stripe_id` (Stripe subscription or customer id), `subscription_tier`.
- Use Stripe webhooks (e.g. `customer.subscription.updated`) to keep `subscription` in sync.
- Backend can then enforce tier (e.g. limit number of jobs, or feature flags) by reading `subscription` for the current `user_id`.

### 3.4 Phone/SMS in production

- Supabase Phone auth in production often requires **Supabase Pro** or your own **Twilio** (or similar) integration. Configure the provider in Supabase and document the chosen approach for your team.

---

## 4. Troubleshooting

| Issue | What to check |
|-------|----------------|
| 401 on API calls | Frontend sends `Authorization: Bearer <token>` from `session.access_token` after Supabase sign-in. Backend verifies via JWKS (`SUPABASE_URL` set). |
| “Auth not configured” (503) | Backend env: `SUPABASE_URL` must be set so JWKS can be fetched from `{SUPABASE_URL}/auth/v1/.well-known/jwks.json`. |
| “Job not found” after upload | Backend has `DATABASE_URL` set; migration has been run; `jobs` table exists. Check backend logs for DB errors. |
| Social login redirect fails | Supabase Auth URL configuration includes the exact redirect URL (scheme + host + path). Frontend uses same project (same URL and Publishable key). |
| CORS errors | Frontend origin is in backend `ALLOWED_ORIGINS` and in Supabase Auth redirect URLs. Backend sends correct CORS headers (already configured in the app). |

---

## 5. Supabase: new API keys and JWT signing

Supabase has moved to **new API keys** (Publishable `sb_publishable_...` and Secret `sb_secret_...`) and **new JWT signing keys**. Legacy anon/service_role API keys can be disabled in the dashboard.

**This app is configured for the new approach:**

- **Frontend:** Use the **Publishable key** from Project Settings → API Keys (not Legacy API Keys). Set `VITE_SUPABASE_PUBLISHABLE_KEY` in `frontend/.env`.
- **Backend:** Uses **JWKS only**. Set `SUPABASE_URL`; the backend fetches public keys from [JWKS](https://supabase.com/docs/guides/auth/signing-keys) (`/auth/v1/.well-known/jwks.json`) to verify user access tokens. No legacy JWT secret or anon key is used on the backend.

---

## 6. Reference

- **Auth**: [backend/auth.py](../backend/auth.py) — JWT verification; [frontend/src/contexts/AuthContext.jsx](../frontend/src/contexts/AuthContext.jsx) — session state.
- **DB**: [backend/store.py](../backend/store.py) — job persistence; [supabase/migrations/](../supabase/migrations/) — schema.
- **Env**: [backend/.env.example](../backend/.env.example), [frontend/.env.example](../frontend/.env.example).
- **Deploy**: [DEPLOY_STEPS.md](DEPLOY_STEPS.md).
- **Supabase JWT Signing Keys**: [Supabase docs](https://supabase.com/docs/guides/auth/signing-keys).
