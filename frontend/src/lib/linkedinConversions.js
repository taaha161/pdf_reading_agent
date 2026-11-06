// LinkedIn Insight Tag conversions for the scan-first funnel, fired before
// signup so LinkedIn gets more (earlier) signals to optimize on than signups
// alone. Signup itself is tracked in trackSignup.js.
//
// Campaign Manager → Measure → Conversion tracking. Each ID must be an
// Insight Tag, event-specific conversion: lintrk() events are ignored by
// Conversions API (Direct API) conversions. Public values, safe in client code.
export const LINKEDIN_TRIAL_SCAN_CONVERSION_ID = 30227860; // "Free scan completed (Insight Tag)"
export const LINKEDIN_SPREADSHEET_EMAILED_CONVERSION_ID = 30227868; // "Spreadsheet emailed (Insight Tag)"

/**
 * Fire a LinkedIn conversion once per dedupeKey (e.g. a job id) in this
 * browser, so re-renders or reloads of the same result don't double-count.
 */
export function trackLinkedInConversion(conversionId, dedupeKey) {
  if (typeof window === "undefined" || !conversionId) return;
  if (dedupeKey) {
    const key = `li_conv:${conversionId}:${dedupeKey}`;
    try {
      if (localStorage.getItem(key)) return;
      localStorage.setItem(key, "1");
    } catch {
      // storage blocked: still fire once for this call
    }
  }
  if (typeof window.lintrk === "function") {
    window.lintrk("track", { conversion_id: conversionId });
  }
}
