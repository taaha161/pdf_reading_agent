-- Optional in-app feedback, prompted after a user's second scan.
CREATE TABLE IF NOT EXISTS public.scan_feedback (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT,
  job_id UUID,
  rating SMALLINT CHECK (rating BETWEEN 1 AND 5),
  comment TEXT,
  contact_ok BOOLEAN NOT NULL DEFAULT FALSE,
  client_ip_hash TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scan_feedback_created_at
  ON public.scan_feedback (created_at DESC);

-- Backend-only table (accessed via DATABASE_URL); no client access.
ALTER TABLE public.scan_feedback ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE public.scan_feedback IS
  'Optional feedback from the post-scan prompt. rating 1-5 and/or free-text comment; contact_ok = user agreed to be emailed about it.';
