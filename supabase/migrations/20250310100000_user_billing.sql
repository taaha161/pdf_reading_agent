-- Billing: user_billing table, jobs.conversion_mode, optional billing_usage_log.
-- Idempotent: safe to run when columns/tables already exist.

-- Jobs: add conversion_mode (fast, balanced, accurate) for billing and UI
ALTER TABLE public.jobs
  ADD COLUMN IF NOT EXISTS conversion_mode TEXT;

-- User billing: balance and Stripe ids
CREATE TABLE IF NOT EXISTS public.user_billing (
  user_id TEXT PRIMARY KEY,
  balance_cents INT NOT NULL DEFAULT 0,
  stripe_customer_id TEXT UNIQUE,
  stripe_subscription_id TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_user_billing_stripe_customer_id
  ON public.user_billing (stripe_customer_id)
  WHERE stripe_customer_id IS NOT NULL;

-- Optional: usage log for audit
CREATE TABLE IF NOT EXISTS public.billing_usage_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT NOT NULL,
  job_id UUID NOT NULL,
  amount_cents INT NOT NULL,
  balance_after_cents INT NOT NULL,
  conversion_mode TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_billing_usage_log_user_created
  ON public.billing_usage_log (user_id, created_at DESC);

-- RLS: users can only read/update their own billing row
ALTER TABLE public.user_billing ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can manage own billing" ON public.user_billing;
CREATE POLICY "Users can manage own billing"
  ON public.user_billing
  FOR ALL
  USING (user_id = auth.uid()::text)
  WITH CHECK (user_id = auth.uid()::text);

-- Service role can do anything (for webhooks)
DROP POLICY IF EXISTS "Service role full access user_billing" ON public.user_billing;
CREATE POLICY "Service role full access user_billing"
  ON public.user_billing
  FOR ALL
  USING (auth.jwt() ->> 'role' = 'service_role')
  WITH CHECK (auth.jwt() ->> 'role' = 'service_role');
