// GA4 events for the funnel: scan_completed, sign_up, spreadsheet_emailed.
//
// GTM (GTM-TKPGJ7DD) only loads the Google tag (G-75SRB0NNXY); it has no GA4
// event tags, so a plain dataLayer.push({ event }) never reaches GA4. gtag()
// commands do: the Google tag reads them from the same dataLayer. Each event is
// also pushed in GTM's format so GTM triggers keep working.
//
// subscribe and purchase are sent server-side from the Stripe webhook
// (backend/services/ga4_mp.py) using the ids from getGaIds() below.

export function trackEvent(name, params = {}) {
  if (typeof window === "undefined") return;
  try {
    const w = window;
    w.dataLayer = w.dataLayer || [];
    w.dataLayer.push({ event: name, ...params });
    if (typeof w.gtag !== "function") {
      w.gtag = function gtag() {
        w.dataLayer.push(arguments);
      };
    }
    w.gtag("event", name, params);
  } catch {
    /* analytics must never break the app */
  }
}

function readCookie(match) {
  try {
    for (const part of document.cookie.split(";")) {
      const [k, ...v] = part.trim().split("=");
      if (match(k)) return decodeURIComponent(v.join("="));
    }
  } catch {
    /* cookies blocked */
  }
  return null;
}

/**
 * The browser's GA4 client id and session id, read from the _ga / _ga_<stream>
 * cookies. Sent with checkout so server-side events join the visitor's session.
 */
export function getGaIds() {
  const ga = readCookie((k) => k === "_ga"); // GA1.1.<random>.<timestamp>
  const clientId = ga?.split(".").slice(-2).join(".") || null;
  const stream = readCookie((k) => k.startsWith("_ga_")); // GS1.1.<sid>... or GS2.1.s<sid>$...
  const sessionId = stream?.match(/^GS\d\.\d\.s?(\d+)/)?.[1] || null;
  return {
    ga_client_id: clientId && /^\d+\.\d+$/.test(clientId) ? clientId : null,
    ga_session_id: sessionId,
  };
}
