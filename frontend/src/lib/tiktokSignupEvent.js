/**
 * Fire-and-forget TikTok Events API (server) after successful email signup.
 * Requires TIKTOK_EVENTS_ACCESS_TOKEN on the host (e.g. Vercel).
 */
export function sendTikTokSignupEvent({ email }) {
  if (typeof window === "undefined" || !email?.trim()) return;

  const ttclid = new URLSearchParams(window.location.search).get("ttclid") || undefined;
  const ttpRow = document.cookie.split("; ").find((row) => row.startsWith("_ttp="));
  const ttp = ttpRow?.split("=")[1];

  void fetch("/api/tiktok-signup-event", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email: email.trim(),
      url: window.location.href,
      referrer: typeof document !== "undefined" ? document.referrer || "" : "",
      ...(ttclid && { ttclid }),
      ...(ttp && { ttp }),
    }),
  }).catch(() => {});
}
