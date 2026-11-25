-- Subscriber-only page packs (10/30/100) go in their own bucket: they never expire
-- but can only be spent while the user has an active subscription. Bulk packs,
-- promo/review bonuses and every pack bought before this change stay in pack_pages.
ALTER TABLE public.user_billing
  ADD COLUMN IF NOT EXISTS sub_pack_pages integer NOT NULL DEFAULT 0;

-- Canceled subscriptions were never cleared (set_stripe_ids COALESCEd a NULL id back to
-- the old one). Fixed in code; stale ids are cleared by a one-off script checked against Stripe.
