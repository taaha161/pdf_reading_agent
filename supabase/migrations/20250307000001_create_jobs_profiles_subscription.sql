-- Jobs: per-user statement processing results.
-- raw_text and currency support existing CSV/markdown/chat API; plan schema is id, user_id, transactions, created_at.
CREATE TABLE IF NOT EXISTS public.jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  transactions JSONB NOT NULL DEFAULT '[]',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  raw_text TEXT,
  currency TEXT
);

CREATE INDEX IF NOT EXISTS idx_jobs_user_created ON public.jobs (user_id, created_at DESC);

-- Profiles: extended user info; id matches Supabase auth.users(id).
CREATE TABLE IF NOT EXISTS public.profiles (
  id UUID PRIMARY KEY REFERENCES auth.users (id) ON DELETE CASCADE,
  email TEXT,
  phone TEXT,
  display_name TEXT,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  stripe_id TEXT
);

-- Subscription: one row per user for Stripe billing.
CREATE TABLE IF NOT EXISTS public.subscription (
  user_id UUID PRIMARY KEY REFERENCES auth.users (id) ON DELETE CASCADE,
  stripe_id TEXT,
  subscription_tier TEXT
);

-- RLS (optional): enable Row Level Security so Supabase client can only read/write own rows.
ALTER TABLE public.jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.subscription ENABLE ROW LEVEL SECURITY;

-- Policies: users can only access their own data (backend uses service role and bypasses RLS).
CREATE POLICY "Users can manage own jobs" ON public.jobs
  FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users can manage own profile" ON public.profiles
  FOR ALL USING (auth.uid() = id);

CREATE POLICY "Users can view own subscription" ON public.subscription
  FOR ALL USING (auth.uid() = user_id);
