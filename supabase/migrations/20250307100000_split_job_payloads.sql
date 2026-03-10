-- Split purgeable job data into job_payloads so we can purge without losing job count.
-- jobs: id, user_id, created_at, incognito (kept for rate limiting).
-- job_payloads: job_id, transactions, raw_text, currency (purgeable).
-- Idempotent: safe when jobs does not exist, when already split, or when policy already exists.

-- Ensure jobs table exists (fresh DB: create in final shape; existing DB: alter)
CREATE TABLE IF NOT EXISTS public.jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  incognito BOOLEAN NOT NULL DEFAULT false
);

ALTER TABLE public.jobs
  ADD COLUMN IF NOT EXISTS incognito BOOLEAN NOT NULL DEFAULT false;

CREATE TABLE IF NOT EXISTS public.job_payloads (
  job_id UUID PRIMARY KEY REFERENCES public.jobs (id) ON DELETE CASCADE,
  transactions JSONB NOT NULL DEFAULT '[]',
  raw_text TEXT,
  currency TEXT
);

-- Migrate existing data only if jobs still has the old columns
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'jobs' AND column_name = 'transactions'
  ) THEN
    INSERT INTO public.job_payloads (job_id, transactions, raw_text, currency)
    SELECT id, transactions, raw_text, currency FROM public.jobs
    ON CONFLICT (job_id) DO NOTHING;
  END IF;
END $$;

ALTER TABLE public.jobs DROP COLUMN IF EXISTS transactions;
ALTER TABLE public.jobs DROP COLUMN IF EXISTS raw_text;
ALTER TABLE public.jobs DROP COLUMN IF EXISTS currency;

ALTER TABLE public.job_payloads ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can manage own job payloads" ON public.job_payloads;
CREATE POLICY "Users can manage own job payloads"
  ON public.job_payloads
  FOR ALL
  USING (
    EXISTS (SELECT 1 FROM public.jobs j WHERE j.id = job_payloads.job_id AND j.user_id = auth.uid())
  );
