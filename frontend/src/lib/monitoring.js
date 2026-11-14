/**
 * Error monitoring (Sentry). Off unless VITE_SENTRY_DSN is set at build time.
 *
 * Privacy: users upload bank statements, so we never send session replays,
 * IPs or cookies; URL query strings and hashes are stripped (Supabase puts auth
 * tokens in the reset-password hash); console breadcrumbs are dropped except
 * errors; users are identified by Supabase id only.
 */
import * as Sentry from "@sentry/react";

const DSN = import.meta.env.VITE_SENTRY_DSN || "";
let enabled = false;

/** "https://x.com/reset-password?code=1#access_token=abc" -> "https://x.com/reset-password" */
export function stripUrl(url) {
  if (typeof url !== "string") return url;
  return url.split(/[?#]/)[0];
}

function scrubBreadcrumb(crumb) {
  if (crumb.category === "console" && crumb.level !== "error") return null;
  const data = crumb.data;
  if (data) {
    for (const key of ["url", "from", "to"]) {
      if (typeof data[key] === "string") data[key] = stripUrl(data[key]);
    }
  }
  return crumb;
}

export function scrubEvent(event) {
  if (event.request) {
    if (event.request.url) event.request.url = stripUrl(event.request.url);
    delete event.request.cookies;
    delete event.request.query_string;
    if (event.request.headers) {
      delete event.request.headers.Referer;
      delete event.request.headers.referer;
    }
  }
  if (event.breadcrumbs) {
    event.breadcrumbs = event.breadcrumbs.map(scrubBreadcrumb).filter(Boolean);
  }
  return event;
}

export function initMonitoring() {
  if (!DSN || enabled) return;
  Sentry.init({
    dsn: DSN,
    environment: import.meta.env.MODE,
    release: import.meta.env.VITE_RELEASE || undefined,
    sendDefaultPii: false,
    tracesSampleRate: 0,
    ignoreErrors: [
      "ResizeObserver loop limit exceeded",
      "ResizeObserver loop completed with undelivered notifications",
      // Browser extensions / injected scripts
      /^Non-Error promise rejection captured/,
    ],
    denyUrls: [/^chrome-extension:\/\//, /^moz-extension:\/\//, /^safari-web-extension:\/\//],
    beforeSend: scrubEvent,
    beforeBreadcrumb: scrubBreadcrumb,
  });
  enabled = true;
}

export function setMonitoringUser(userId) {
  if (!enabled) return;
  Sentry.setUser(userId ? { id: userId } : null);
}

export function captureError(error, context = {}) {
  if (!enabled) return;
  Sentry.captureException(error, context);
}

export function captureMessage(message, { level = "error", tags, extra } = {}) {
  if (!enabled) return;
  Sentry.captureMessage(message, { level, tags, extra });
}
