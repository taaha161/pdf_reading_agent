// First-party ad attribution: which campaign brought a visitor in. Saved into
// the Supabase user's metadata at signup so paying users can be traced back to
// a source (the database otherwise can't tell a LinkedIn signup from organic).
//
// Last non-empty touch wins: any landing with UTM params or a LinkedIn click
// id (li_fat_id, or Google gclid/gbraid/wbraid) overwrites the stored value. Kept 30 days. The marketing site
// (marketing/src/layouts/Base.astro) writes the same key in the same format.
const KEY = "bss_attribution";
const TTL_MS = 30 * 24 * 60 * 60 * 1000;
const PARAMS = ["utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term", "li_fat_id", "gclid", "gbraid", "wbraid"];
const MAX_LEN = 200;

/** Store attribution from the current URL, if it carries any campaign params. */
export function captureAttributionFromUrl() {
  try {
    const params = new URLSearchParams(window.location.search);
    const touch = {};
    for (const k of PARAMS) {
      const v = params.get(k)?.trim();
      if (v) touch[k] = v.slice(0, MAX_LEN);
    }
    if (!Object.keys(touch).length) return;
    touch.landing_path = window.location.pathname.slice(0, MAX_LEN);
    touch.at = new Date().toISOString();
    localStorage.setItem(KEY, JSON.stringify(touch));
  } catch {
    /* storage blocked: attribution just won't persist */
  }
}

/** Stored attribution for this browser, or null if none / expired. */
export function getAttribution() {
  try {
    const touch = JSON.parse(localStorage.getItem(KEY) || "null");
    if (!touch || typeof touch !== "object") return null;
    const at = Date.parse(touch.at ?? "");
    if (Number.isNaN(at) || Date.now() - at > TTL_MS) return null;
    return touch;
  } catch {
    return null;
  }
}
