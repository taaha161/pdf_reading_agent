-- Review reward: a user who leaves a G2 review (any rating) can claim 100 pack pages, once per account.
-- The claim is checked by hand and granted with backend/scripts/grant_review_reward.py.
CREATE TABLE IF NOT EXISTS public.review_claims (
  user_id TEXT PRIMARY KEY,
  platform TEXT NOT NULL DEFAULT 'g2',
  proof TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'granted', 'rejected')),
  pages_granted INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  decided_at TIMESTAMPTZ
);

-- Backend-only table (accessed via DATABASE_URL); no client access.
ALTER TABLE public.review_claims ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE public.review_claims IS
  'One review-reward claim per account. proof = review link or reviewer name the user gave. status pending -> granted/rejected by hand.';
