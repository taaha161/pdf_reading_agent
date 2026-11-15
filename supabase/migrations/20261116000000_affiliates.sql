-- Affiliate program.
--   affiliates:             partners we set up by hand (admin API), each with a
--                           unique code, their own revenue-share percentage, and an
--                           optional discount for the users they refer.
--   affiliate_referrals:    which affiliate brought in a user (one per user, set
--                           once, only for accounts that signed up with the code).
--   affiliate_commissions:  one row per payment by a referred user; the commission
--                           is computed at payment time with the affiliate's
--                           percentage then, so later rate changes don't rewrite history.
-- Backend-only tables: RLS on with no policies = no access via the public REST API.

CREATE TABLE IF NOT EXISTS public.affiliates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  email TEXT,
  code TEXT NOT NULL UNIQUE,                    -- stored lowercase
  revenue_share_pct NUMERIC(5, 2) NOT NULL CHECK (revenue_share_pct >= 0 AND revenue_share_pct <= 100),
  commission_months INT CHECK (commission_months IS NULL OR commission_months > 0), -- NULL = lifetime
  -- Discount for users who sign up with the code (0 = none).
  discount_pct NUMERIC(5, 2) NOT NULL DEFAULT 0 CHECK (discount_pct >= 0 AND discount_pct <= 100),
  discount_months INT CHECK (discount_months IS NULL OR discount_months > 0), -- NULL = forever
  discount_packs BOOLEAN NOT NULL DEFAULT FALSE,  -- also discount page packs during the discount window
  stripe_coupon_id TEXT,                          -- created lazily from discount_pct/months; cleared when they change
  active BOOLEAN NOT NULL DEFAULT TRUE,
  notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.affiliate_referrals (
  user_id TEXT PRIMARY KEY,
  affiliate_id UUID NOT NULL REFERENCES public.affiliates (id),
  code TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_affiliate_referrals_affiliate
  ON public.affiliate_referrals (affiliate_id);

CREATE TABLE IF NOT EXISTS public.affiliate_commissions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  affiliate_id UUID NOT NULL REFERENCES public.affiliates (id),
  user_id TEXT NOT NULL,
  source_id TEXT NOT NULL UNIQUE,               -- Stripe invoice / checkout session id (webhook retries are no-ops)
  kind TEXT NOT NULL,                           -- 'subscription' | 'pack'
  amount_cents INT NOT NULL,                    -- what the user paid
  currency TEXT NOT NULL DEFAULT 'usd',
  revenue_share_pct NUMERIC(5, 2) NOT NULL,     -- rate applied
  commission_cents INT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'paid', 'void')),
  paid_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_affiliate_commissions_affiliate_status
  ON public.affiliate_commissions (affiliate_id, status, created_at DESC);

ALTER TABLE public.affiliates ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.affiliate_referrals ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.affiliate_commissions ENABLE ROW LEVEL SECURITY;
