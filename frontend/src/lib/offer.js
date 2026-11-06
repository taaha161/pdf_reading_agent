// Ad-campaign offer carried from a marketing landing page (e.g. /lp/linkedin)
// through signup to Stripe checkout. The server validates the code against its
// own allowlist, so this is only a hint — never trusted for pricing.
const KEY = "bss_offer";
const TTL_MS = 30 * 24 * 60 * 60 * 1000; // keep the offer for 30 days

export const OFFERS = {
  linkedin1m: { label: "LinkedIn offer: your first month is free", cta: "Start free month" },
};

/** Persist ?offer=<code> from the current URL if it's a known offer. */
export function captureOfferFromUrl() {
  try {
    const code = new URLSearchParams(window.location.search).get("offer")?.trim().toLowerCase();
    if (code && OFFERS[code]) {
      localStorage.setItem(KEY, JSON.stringify({ code, at: Date.now() }));
    }
  } catch {
    /* storage blocked: offer just won't persist */
  }
}

// Allow for clock skew between this browser and the auth server.
const SIGNUP_SKEW_MS = 10 * 60 * 1000;

/**
 * Active offer code for this signed-in user, or null.
 *
 * The offer is stored per browser, so on its own it would follow any account
 * that signs in here (e.g. an existing customer who clicked an ad link once).
 * It only applies to accounts created after the offer link was opened.
 */
export function getOffer(user) {
  try {
    const saved = JSON.parse(localStorage.getItem(KEY) || "null");
    if (!saved || !OFFERS[saved.code] || Date.now() - saved.at >= TTL_MS) return null;
    const createdAt = Date.parse(user?.created_at ?? "");
    if (Number.isNaN(createdAt) || createdAt < saved.at - SIGNUP_SKEW_MS) return null;
    return saved.code;
  } catch {
    /* ignore */
  }
  return null;
}

export function clearOffer() {
  try {
    localStorage.removeItem(KEY);
  } catch {
    /* ignore */
  }
}
