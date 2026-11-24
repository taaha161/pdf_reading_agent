/**
 * Review reward: signed-in users running low on pages are offered 100 pack pages for a G2
 * review (any rating, so it complies with G2's incentive rules and the FTC review rule).
 * Trustpilot bans incentivized reviews, so it only gets a plain link with no reward.
 * Set VITE_G2_REVIEW_URL to an empty string to turn the card off.
 */
export const G2_REVIEW_URL =
  import.meta.env.VITE_G2_REVIEW_URL ?? "https://www.g2.com/products/bank-statement-scanner/take_survey";
export const TRUSTPILOT_REVIEW_URL = import.meta.env.VITE_TRUSTPILOT_REVIEW_URL || "";
export const REVIEW_REWARD_PAGES = 100; // keep in sync with backend store.REVIEW_REWARD_PAGES
export const REVIEW_PROMPT_AT_PAGES = 50;
export const REVIEW_PROMPT_AFTER_SCANS = 3;

const DISMISSED_KEY = "bss_review_reward_dismissed_at";
const SNOOZE_MS = 7 * 24 * 60 * 60 * 1000;

function dismissedRecently() {
  try {
    const at = Number(localStorage.getItem(DISMISSED_KEY) || 0);
    return at > 0 && Date.now() - at < SNOOZE_MS;
  } catch {
    return false;
  }
}

export function snoozeReviewReward() {
  try {
    localStorage.setItem(DISMISSED_KEY, String(Date.now()));
  } catch {
    /* storage blocked: the card may show again next visit, which is harmless */
  }
}

/**
 * Show the offer to a signed-in user who has run a few scans (so they've seen it work) or is
 * running low on pages, unless they've already claimed it or snoozed it.
 */
export function reviewRewardDue(usage) {
  if (!G2_REVIEW_URL || !usage?.authenticated) return false;
  if (usage.review_claim != null) return false; // pending, granted, rejected or unknown
  const left = usage.pages_remaining;
  const runningLow = left != null && left <= REVIEW_PROMPT_AT_PAGES;
  const regular = (usage.scan_count ?? 0) >= REVIEW_PROMPT_AFTER_SCANS;
  if (!runningLow && !regular) return false;
  return !dismissedRecently();
}
