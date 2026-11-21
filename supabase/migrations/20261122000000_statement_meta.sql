-- Printed summary box of each statement (bank, last 4 account digits, period, opening/closing
-- balances, total money in/out), read at scan time for reconciliation and account continuity.
-- Lives on job_payloads so purge, incognito and account deletion remove it with the transactions.
-- Idempotent.
ALTER TABLE public.job_payloads ADD COLUMN IF NOT EXISTS statement_meta JSONB;
