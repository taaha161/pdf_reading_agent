/**
 * TikTok ClickButton: browser pixel + server Events API (same event_id for deduplication).
 */
function newEventId() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

export function trackGetStartedClick(placement) {
  if (typeof window === "undefined") return;

  const eventId = newEventId();

  const w = window;
  if (w.ttq) {
    w.ttq.track("ClickButton", {
      content_type: "button",
      content_name: `Get started ${placement}`,
      content_id: placement,
      event_id: eventId,
    });
  }

  const ttclid = new URLSearchParams(w.location.search).get("ttclid") || undefined;
  const ttpRow = document.cookie.split("; ").find((row) => row.startsWith("_ttp="));
  const ttp = ttpRow?.split("=")[1];

  void fetch("/api/tiktok-click-event", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      placement,
      event_id: eventId,
      url: w.location.href,
      referrer: typeof document !== "undefined" ? document.referrer || "" : "",
      ...(ttclid && { ttclid }),
      ...(ttp && { ttp }),
    }),
  }).catch(() => {});
}
