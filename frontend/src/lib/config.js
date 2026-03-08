/**
 * Runtime config: loaded from /api/config on Vercel (server-side env only).
 * In local dev, Vite can inject PUBLIC_* via define in vite.config so we don't need the API.
 */
let cached = null;

export async function loadConfig() {
  if (cached) return cached;
  try {
    const res = await fetch("/api/config", { cache: "default" });
    const data = await res.json().catch(() => ({}));
    if (res.ok && data.supabaseUrl) {
      cached = {
        apiUrl: data.apiUrl || "",
        supabaseUrl: data.supabaseUrl,
        supabasePublishableKey: data.supabasePublishableKey || "",
      };
      return cached;
    }
    if (res.status === 503 && data.message) {
      throw new Error(data.message);
    }
  } catch (e) {
    if (e instanceof Error && e.message.includes("SUPABASE")) throw e;
    // e.g. no /api/config in local dev or network error
  }
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
  };
  return cached;
}

export function getConfig() {
  return cached;
}
