// Affiliate referral code: from a ?ref=<code> link or typed into the signup
// form. The server decides whether it's real and whether this account may
// claim it (new accounts only, once), so this is only a hint.
//
// Pending code lives in localStorage for 30 days so a visitor who clicks an
// affiliate link and signs up later (or via Google) still carries it. The
// marketing site (marketing/src/layouts/Base.astro) writes the same key.
import { claimReferral } from "../api/client";

const PENDING_KEY = "bss_ref";
const TTL_MS = 30 * 24 * 60 * 60 * 1000;
// Server only accepts claims from accounts up to 7 days old; don't bother after that.
const CLAIM_WINDOW_MS = 7 * 24 * 60 * 60 * 1000;
const CODE_RE = /^[a-z0-9][a-z0-9_-]{2,31}$/;

export function normalizeReferralCode(code) {
  const c = String(code ?? "").trim().toLowerCase();
  return CODE_RE.test(c) ? c : null;
}

export function setPendingReferral(code) {
  const c = normalizeReferralCode(code);
  if (!c) return;
  try {
    localStorage.setItem(PENDING_KEY, JSON.stringify({ code: c, at: Date.now() }));
  } catch {
    /* storage blocked */
  }
}

/** Remember ?ref=<code> from the current URL. */
export function captureReferralFromUrl() {
  try {
    const code = new URLSearchParams(window.location.search).get("ref");
    if (code) setPendingReferral(code);
  } catch {
    /* ignore */
  }
}

export function getPendingReferral() {
  try {
    const p = JSON.parse(localStorage.getItem(PENDING_KEY) || "null");
    if (!p || !(Date.now() - p.at < TTL_MS)) return null;
    return normalizeReferralCode(p.code);
  } catch {
    return null;
  }
}

/** Price after `pct`% off, in dollars. Mirrors backend affiliates.discounted_cents ($0.50 minimum). */
export function discountedPrice(price, pct) {
  const cents = Math.round(price * 100);
  const off = Math.round((cents * pct) / 100);
  return Math.max(50, cents - off) / 100;
}

export function formatPrice(dollars) {
  return Number.isInteger(dollars) ? `$${dollars}` : `$${dollars.toFixed(2)}`;
}

/** "20% off the plan for 3 months, plus page packs" style summary of a discount. */
export function describeDiscount(d) {
  if (!d?.pct) return "";
  const length = d.months ? ` for ${d.months} month${d.months === 1 ? "" : "s"}` : "";
  return `${d.pct}% off the monthly plan${length}${d.packs ? ", plus page packs" : ""}`;
}

// In-flight claim, so a checkout right after signup can wait for the discount to bind.
let claimInFlight = Promise.resolve();
export function waitForReferralClaim() {
  return claimInFlight;
}

/**
 * On sign-in of a new account, ask the server to bind it to the referral code
 * it signed up with (email signups: user_metadata; OAuth: pending code).
 * Runs at most once per account per browser.
 */
export function claimReferralIfNew(user, token) {
  claimInFlight = doClaim(user, token).catch(() => {});
  return claimInFlight;
}

async function doClaim(user, token) {
  if (!user?.id || !token) return;
  const age = Date.now() - Date.parse(user.created_at ?? "");
  if (!(age >= 0 && age < CLAIM_WINDOW_MS)) return;
  const code = normalizeReferralCode(user.user_metadata?.referral_code) || getPendingReferral();
  if (!code) return;
  const doneKey = `bss_ref_claimed:${user.id}`;
  try {
    if (localStorage.getItem(doneKey)) return;
  } catch {
    /* ignore */
  }
  const result = await claimReferral(code, token);
  if (!result) return; // network error: retry on next sign-in
  try {
    localStorage.setItem(doneKey, "1");
    localStorage.removeItem(PENDING_KEY);
  } catch {
    /* ignore */
  }
}
