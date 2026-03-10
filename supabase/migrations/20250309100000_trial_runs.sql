-- Track anonymous trial PDF runs (no user data stored; for analytics/counts only).
CREATE TABLE IF NOT EXISTS public.trial_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id UUID NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_trial_runs_created_at ON public.trial_runs (created_at DESC);

COMMENT ON TABLE public.trial_runs IS 'One row per anonymous trial PDF processing; no transaction or PDF data stored.';
