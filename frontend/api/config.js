// Vercel serverless function: serves public config from server-side env only.
// Env vars here are NOT prefixed with VITE_, so they are never embedded in the client bundle.
// Set API_URL, SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY in Vercel → Settings → Environment Variables.

export default function handler(req, res) {
  if (req.method !== "GET") {
    res.setHeader("Allow", "GET");
    return res.status(405).end();
  }
  const supabaseUrl = process.env.SUPABASE_URL || "";
  const supabasePublishableKey =
    process.env.SUPABASE_PUBLISHABLE_KEY || process.env.SUPABASE_ANON_KEY || "";
  if (!supabaseUrl || !supabasePublishableKey) {
    res.setHeader("Content-Type", "application/json");
    return res.status(503).json({
      error: "Config incomplete",
      message:
        "Set SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY in Vercel → Settings → Environment Variables.",
    });
  }
  res.setHeader("Cache-Control", "public, max-age=60");
  res.status(200).json({
    apiUrl: process.env.API_URL || "",
    supabaseUrl,
    supabasePublishableKey,
  });
}
