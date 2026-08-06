-- Durable anonymous trial enforcement: count trial runs per client (by salted
-- IP hash) so clearing the cross-site cookie no longer resets the free-scan
-- limit. Only a one-way hash is stored — never the raw IP.
ALTER TABLE public.trial_runs
  ADD COLUMN IF NOT EXISTS client_ip_hash TEXT;

CREATE INDEX IF NOT EXISTS idx_trial_runs_ip_hash
  ON public.trial_runs (client_ip_hash);

COMMENT ON COLUMN public.trial_runs.client_ip_hash IS
  'HMAC-SHA256 of the client IP (salted with TRIAL_IP_SALT); used to count anonymous trial runs. Never stores the raw IP.';
