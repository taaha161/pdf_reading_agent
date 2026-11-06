/**
 * Fire signup conversion to every ad/analytics tool on the page:
 *  - GTM dataLayer `sign_up` (GA4 recommended event name)
 *  - LinkedIn Insight conversion (needs LINKEDIN_SIGNUP_CONVERSION_ID)
 *  - Microsoft Clarity custom event + tag (filter recordings to converters)
 *
 * Deduped per user id in localStorage so a reload / later login never
 * double-counts the same signup.
 */

// Campaign Manager → Measure → Conversion tracking → "Sign up (Insight Tag)"
// (method: Insight Tag, event-specific). Public value, safe in client code.
// Must be an Insight Tag conversion: lintrk() events are ignored by Conversions
// API (Direct API) conversions. 30227628 is the server-side "Subscription
// purchase (CAPI)" conversion used by backend/services/linkedin_capi.py.
const LINKEDIN_SIGNUP_CONVERSION_ID = 30227852;

// OAuth users have no separate "sign up" step: treat a SIGNED_IN whose account
// was created within this window as a new signup.
const NEW_ACCOUNT_WINDOW_MS = 10 * 60 * 1000;

export function trackSignup({ method, userId }) {
  if (typeof window === "undefined") return;

  if (userId) {
    const key = `signup_tracked:${userId}`;
    try {
      if (localStorage.getItem(key)) return;
      localStorage.setItem(key, "1");
    } catch {
      // storage blocked: still fire once for this call
    }
  }

  const w = window;
  (w.dataLayer = w.dataLayer || []).push({ event: "sign_up", method });

  if (LINKEDIN_SIGNUP_CONVERSION_ID && typeof w.lintrk === "function") {
    w.lintrk("track", { conversion_id: LINKEDIN_SIGNUP_CONVERSION_ID });
  }

  if (typeof w.clarity === "function") {
    w.clarity("event", "sign_up");
    w.clarity("set", "signed_up", method);
  }
}

/** Call on Supabase SIGNED_IN: tracks brand-new OAuth (e.g. Google) accounts. */
export function trackOAuthSignupIfNew(user) {
  const provider = user?.app_metadata?.provider;
  if (!user?.id || !user.created_at || !provider || provider === "email") return;
  const age = Date.now() - new Date(user.created_at).getTime();
  if (age >= 0 && age < NEW_ACCOUNT_WINDOW_MS) {
    trackSignup({ method: provider, userId: user.id });
  }
}
