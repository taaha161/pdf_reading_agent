// Ad-campaign offer carried from a marketing landing page (e.g. /lp/linkedin)
// through signup to Stripe checkout. The server validates the code against its
// own allowlist, so this is only a hint — never trusted for pricing.
//
// Two stages, so the offer only reaches accounts that signed up from the ad:
//  1. Pending (localStorage, 7 days): set when a page opens with ?offer=<code>.
//     Survives new tabs, so a visitor who scans first and signs up later from
//     the "your spreadsheet" email link still gets it.
//  2. Claimed (localStorage): when a brand-new account is created while an
//     offer is pending, it is bound to that account's id and kept for 30 days.
// getOffer(user) only returns an offer claimed by that exact account.
const PENDING_KEY = "bss_offer_pending";
const CLAIMED_KEY = "bss_offer_claimed";
const LEGACY_KEY = "bss_offer"; // pre-binding format; ignored and removed
const TTL_MS = 30 * 24 * 60 * 60 * 1000; // claimed offer lasts 30 days
const PENDING_TTL_MS = 7 * 24 * 60 * 60 * 1000; // unclaimed offer lasts 7 days
// An account counts as "just created" if its created_at is this recent.
const NEW_ACCOUNT_MS = 10 * 60 * 1000;

export const OFFERS = {
  linkedin1m: { label: "LinkedIn offer: your first month is free", cta: "Start free month" },
};

function readJson(storage, key) {
  try {
    return JSON.parse(storage.getItem(key) || "null");
  } catch {
    return null;
  }
}

/** Remember ?offer=<code> from the current URL for this visit, if it's a known offer. */
export function captureOfferFromUrl() {
  try {
    localStorage.removeItem(LEGACY_KEY);
    const code = new URLSearchParams(window.location.search).get("offer")?.trim().toLowerCase();
    if (code && OFFERS[code]) {
      localStorage.setItem(PENDING_KEY, JSON.stringify({ code, at: Date.now() }));
    }
  } catch {
    /* storage blocked: offer just won't persist */
  }
}

function readPending() {
  const pending = readJson(localStorage, PENDING_KEY);
  if (!pending || !OFFERS[pending.code]) return null;
  if (!(Date.now() - pending.at < PENDING_TTL_MS)) return null;
  return pending;
}

/**
 * Bind a pending offer to `user` if the account was just created. Call right
 * after email signup and on OAuth sign-in. Existing accounts never claim it.
 */
export function claimOfferForUser(user) {
  try {
    const pending = readPending();
    if (!pending || !user?.id) return;
    const createdAt = Date.parse(user.created_at ?? "");
    if (Number.isNaN(createdAt) || Date.now() - createdAt > NEW_ACCOUNT_MS) return;
    localStorage.setItem(CLAIMED_KEY, JSON.stringify({ code: pending.code, userId: user.id, at: Date.now() }));
    localStorage.removeItem(PENDING_KEY);
  } catch {
    /* ignore */
  }
}

/** Offer code claimed by this signed-in account, or null. */
export function getOffer(user) {
  const claimed = readJson(localStorage, CLAIMED_KEY);
  if (!claimed || !OFFERS[claimed.code] || !user?.id || claimed.userId !== user.id) return null;
  if (Date.now() - claimed.at >= TTL_MS) return null;
  return claimed.code;
}

export function clearOffer() {
  try {
    localStorage.removeItem(CLAIMED_KEY);
    localStorage.removeItem(PENDING_KEY);
  } catch {
    /* ignore */
  }
}
