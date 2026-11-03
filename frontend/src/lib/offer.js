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

/** Active offer code, or null. */
export function getOffer() {
  try {
    const saved = JSON.parse(localStorage.getItem(KEY) || "null");
    if (saved && OFFERS[saved.code] && Date.now() - saved.at < TTL_MS) return saved.code;
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
