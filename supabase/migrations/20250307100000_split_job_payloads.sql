-- Split purgeable job data into job_payloads so we can purge without losing job count.
-- jobs: id, user_id, created_at, incognito (kept for rate limiting).
-- job_payloads: job_id, transactions, raw_text, currency (purgeable).

ALTER TABLE public.jobs
  ADD COLUMN IF NOT EXISTS incognito BOOLEAN NOT NULL DEFAULT false;

CREATE TABLE IF NOT EXISTS public.job_payloads (
  job_id UUID PRIMARY KEY REFERENCES public.jobs (id) ON DELETE CASCADE,
  transactions JSONB NOT NULL DEFAULT '[]',
  raw_text TEXT,
  currency TEXT
);

-- Migrate existing data into job_payloads
INSERT INTO public.job_payloads (job_id, transactions, raw_text, currency)
SELECT id, transactions, raw_text, currency FROM public.jobs
ON CONFLICT (job_id) DO NOTHING;

ALTER TABLE public.jobs DROP COLUMN IF EXISTS transactions;
ALTER TABLE public.jobs DROP COLUMN IF EXISTS raw_text;
ALTER TABLE public.jobs DROP COLUMN IF EXISTS currency;

ALTER TABLE public.job_payloads ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own job payloads"
  ON public.job_payloads
  FOR ALL
  USING (
    EXISTS (SELECT 1 FROM public.jobs j WHERE j.id = job_payloads.job_id AND j.user_id = auth.uid())
  );
