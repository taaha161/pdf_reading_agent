/**
 * Runtime config: loaded from /api/config on Vercel (server-side env only).
 * In local dev, Vite can inject PUBLIC_* via define in vite.config so we don't need the API.
 */
let cached = null;

const RETRY_DELAYS_MS = [400, 1200, 3000];
const FETCH_TIMEOUT_MS = 8000;

/** Shown to visitors when config cannot be fetched (network blip, timeout). */
export const CONFIG_NETWORK_ERROR =
  "We couldn't connect to Bank Statement Scanner. Check your connection and try again.";

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/**
 * Fetch /api/config, retrying transient failures (network error, timeout, 5xx other than
 * a config-incomplete 503). Returns parsed data, or null when the endpoint does not exist
 * (local dev). Throws for a misconfigured deployment.
 */
async function fetchRemoteConfig() {
  for (let attempt = 0; attempt <= RETRY_DELAYS_MS.length; attempt++) {
    if (attempt > 0) await sleep(RETRY_DELAYS_MS[attempt - 1]);
    let res;
    try {
      res = await fetch("/api/config", {
        cache: attempt === 0 ? "default" : "no-store",
        signal: AbortSignal.timeout ? AbortSignal.timeout(FETCH_TIMEOUT_MS) : undefined,
      });
    } catch {
      continue; // network error or timeout: retry
    }
    const data = await res.json().catch(() => null);
    if (res.ok && data?.supabaseUrl) return data;
    if (res.status === 503 && data?.message) throw new Error(data.message); // env vars missing
    if (res.status === 404 || (res.ok && data === null)) return null; // no endpoint (local dev)
    // other 5xx or bad body: retry
  }
  return import.meta.env.PROD ? "unreachable" : null;
}

export async function loadConfig() {
  if (cached) return cached;
  const data = await fetchRemoteConfig();
  if (data && data !== "unreachable") {
    cached = {
      apiUrl: data.apiUrl || "",
      supabaseUrl: data.supabaseUrl,
      supabasePublishableKey: data.supabasePublishableKey || "",
      recaptchaSiteKey: data.recaptchaSiteKey || "",
      googleClientId: data.googleClientId || "",
      googleApiKey: data.googleApiKey || "",
      googleAppId: data.googleAppId || "",
    };
    return cached;
  }
  if (data === "unreachable") throw new Error(CONFIG_NETWORK_ERROR);
  // Dev fallback: use values injected by Vite (vite.config define), or defaults
  const supabaseUrl = import.meta.env.PUBLIC_SUPABASE_URL || "";
  const supabasePublishableKey =
    import.meta.env.PUBLIC_SUPABASE_PUBLISHABLE_KEY ||
    import.meta.env.PUBLIC_SUPABASE_ANON_KEY ||
    "";
  if (!supabaseUrl && typeof import.meta.env.PUBLIC_API_URL === "undefined") {
    throw new Error(
      "Config unavailable. In production, set API_URL, SUPABASE_URL, and SUPABASE_PUBLISHABLE_KEY in Vercel → Settings → Environment Variables."
    );
  }
  cached = {
    apiUrl:
      typeof import.meta.env.PUBLIC_API_URL !== "undefined"
        ? import.meta.env.PUBLIC_API_URL
        : "http://localhost:8000",
    supabaseUrl,
    supabasePublishableKey,
    recaptchaSiteKey: import.meta.env.PUBLIC_RECAPTCHA_SITE_KEY || "",
    googleClientId: import.meta.env.PUBLIC_GOOGLE_CLIENT_ID || "",
    googleApiKey: import.meta.env.PUBLIC_GOOGLE_API_KEY || "",
    googleAppId: import.meta.env.PUBLIC_GOOGLE_APP_ID || "",
  };
  return cached;
}

export function getConfig() {
  return cached;
}
