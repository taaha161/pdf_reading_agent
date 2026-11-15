-- Lock down tables exposed through Supabase's REST API (PostgREST).
--
-- The backend connects as the table owner (postgres, BYPASSRLS), so none of
-- this affects it. The frontend never reads these tables directly; it goes
-- through the backend API. These policies only limit what someone holding the
-- public anon key or a user JWT can do via /rest/v1.

-- trial_runs and billing_usage_log had RLS disabled, so anyone with the public
-- anon key could read every row (job ids, IP hashes, user ids, spend).
-- RLS on with no policies = no access for anon/authenticated.
ALTER TABLE public.trial_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.billing_usage_log ENABLE ROW LEVEL SECURITY;

-- user_billing: users could INSERT/UPDATE their own row (e.g. set balance_cents).
-- Make it read-only for the owner; only the backend writes balances.
DROP POLICY IF EXISTS "Users can manage own billing" ON public.user_billing;
DROP POLICY IF EXISTS "Users can view own billing" ON public.user_billing;
CREATE POLICY "Users can view own billing"
  ON public.user_billing
  FOR SELECT
  USING (user_id = auth.uid()::text);

-- subscription: same problem (users could set their own subscription_tier).
DO $$
BEGIN
  IF to_regclass('public.subscription') IS NOT NULL THEN
    DROP POLICY IF EXISTS "Users can view own subscription" ON public.subscription;
    CREATE POLICY "Users can view own subscription"
      ON public.subscription
      FOR SELECT
      USING (auth.uid() = user_id);
  END IF;
END $$;
