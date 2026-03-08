import { createClient } from "@supabase/supabase-js";

let client = null;

export function initSupabase(url, publishableKey) {
  client = createClient(url || "", publishableKey || "");
  return client;
}

export function getSupabase() {
  if (!client) throw new Error("Supabase not initialized. Call initSupabase after loadConfig().");
  return client;
}

/** @deprecated Use getSupabase() after init. Kept for backwards compatibility during init. */
export const supabase = new Proxy(
  {},
  {
    get(_, prop) {
      return getSupabase()[prop];
    },
  }
);
