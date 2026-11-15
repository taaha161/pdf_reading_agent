-- Page-based pricing.
--   Anonymous: 10 free pages per client (counted from trial_runs.pages by IP hash).
--   Signed in: 100 free pages valid 30 days (granted lazily on first billing lookup).
--   $10/month plan: 100 pages per billing cycle (resets, no rollover).
--   Page packs: 10/$2, 30/$5, 100/$10 — never expire.
-- Accurate mode costs 2 pages per PDF page; fast/balanced cost 1.
-- balance_cents is kept for history but no longer used.

ALTER TABLE public.user_billing
  ADD COLUMN IF NOT EXISTS free_pages INT NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS free_expires_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS plan_pages INT NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS pack_pages INT NOT NULL DEFAULT 0;

ALTER TABLE public.trial_runs
  ADD COLUMN IF NOT EXISTS pages INT;

COMMENT ON COLUMN public.trial_runs.pages IS
  'Pages charged for this free run (anonymous: counts toward the 10-page limit). NULL for runs before page pricing.';

ALTER TABLE public.billing_usage_log
  ADD COLUMN IF NOT EXISTS pages INT;

-- One-time fresh start for existing rows (only rows not yet converted):
--   subscribers: 100 plan pages + any cents above the $10 allowance at $0.10/page
--   everyone else: leftover cents at $0.10/page
-- free_expires_at stays NULL, so every existing account gets its 100 free pages
-- for 30 days on its next visit.
UPDATE public.user_billing
SET
  plan_pages = CASE WHEN stripe_subscription_id IS NOT NULL THEN 100 ELSE 0 END,
  pack_pages = CASE
    WHEN stripe_subscription_id IS NOT NULL THEN GREATEST(0, balance_cents - 1000) / 10
    ELSE GREATEST(0, balance_cents) / 10
  END,
  balance_cents = 0,
  updated_at = NOW()
WHERE (balance_cents > 0 OR stripe_subscription_id IS NOT NULL)
  AND plan_pages = 0 AND pack_pages = 0;
