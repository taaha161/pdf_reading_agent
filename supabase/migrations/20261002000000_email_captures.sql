-- Emails captured from anonymous users (e.g. "Email me the spreadsheet").
-- Used to follow up with trial users who never sign up. No transaction data
-- is stored here; the spreadsheet is emailed and discarded.
CREATE TABLE IF NOT EXISTS public.email_captures (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT NOT NULL,
  source TEXT NOT NULL DEFAULT 'email_spreadsheet',
  job_id UUID,
  marketing_opt_in BOOLEAN NOT NULL DEFAULT FALSE,
  client_ip_hash TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_email_captures_email
  ON public.email_captures (lower(email));

CREATE INDEX IF NOT EXISTS idx_email_captures_created_at
  ON public.email_captures (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_email_captures_job_id
  ON public.email_captures (job_id);

-- Backend-only table (accessed via DATABASE_URL); no client access.
ALTER TABLE public.email_captures ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE public.email_captures IS
  'Emails from anonymous users who asked for their spreadsheet by email. marketing_opt_in = consented to follow-up emails.';
