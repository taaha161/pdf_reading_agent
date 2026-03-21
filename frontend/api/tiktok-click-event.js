// TikTok Events API — ClickButton for “Get started” CTAs (pairs with client ttq.track + same event_id).

const ENDPOINT = "https://business-api.tiktok.com/open_api/v1.3/event/track/";
const DEFAULT_PIXEL = "D6VG41RC77UCSLHQUEDG";

function clientIp(req) {
  const xff = req.headers["x-forwarded-for"];
  if (typeof xff === "string") {
    const first = xff.split(",")[0]?.trim();
    if (first) return first;
  }
  const real = req.headers["x-real-ip"];
  if (typeof real === "string" && real) return real;
  return "";
}

function parseBody(req) {
  if (req.body == null) return {};
  if (typeof req.body === "string") {
    try {
      return JSON.parse(req.body);
    } catch {
      return null;
    }
  }
  return req.body;
}

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export default async function handler(req, res) {
  if (req.method !== "POST") {
    res.setHeader("Allow", "POST");
    return res.status(405).end();
  }

  const token = process.env.TIKTOK_EVENTS_ACCESS_TOKEN;
  if (!token) {
    return res.status(200).json({ ok: false, skipped: true });
  }

  const body = parseBody(req);
  if (body === null) {
    return res.status(400).json({ ok: false, error: "invalid_json" });
  }

  const eventId = typeof body.event_id === "string" ? body.event_id.trim() : "";
  if (!eventId || !UUID_RE.test(eventId)) {
    return res.status(400).json({ ok: false, error: "invalid_event_id" });
  }

  const placement = typeof body.placement === "string" ? body.placement.trim().slice(0, 64) : "cta";
  const url = typeof body.url === "string" ? body.url : "";
  const referrer = typeof body.referrer === "string" ? body.referrer : "";
  const ttclid = typeof body.ttclid === "string" && body.ttclid.trim() ? body.ttclid.trim() : undefined;
  const ttp = typeof body.ttp === "string" && body.ttp.trim() ? body.ttp.trim() : undefined;

  const pixelCode = process.env.TIKTOK_PIXEL_CODE || DEFAULT_PIXEL;
  const userAgent = req.headers["user-agent"] || "";
  const ip = clientIp(req);

  const context = {
    ip,
    user_agent: userAgent,
    page: {
      ...(url && { url }),
      ...(referrer && { referrer }),
    },
    ...(ttp && { user: { ttp } }),
    ...(ttclid && { ad: { callback: ttclid } }),
  };

  const payload = {
    event_source: "web",
    event_source_id: pixelCode,
    data: [
      {
        event: "ClickButton",
        event_time: Math.floor(Date.now() / 1000),
        event_id: eventId,
        context,
        properties: {
          content_type: "button",
          content_name: `Get started ${placement}`,
          content_id: placement,
        },
      },
    ],
  };

  try {
    const response = await fetch(ENDPOINT, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Access-Token": token,
      },
      body: JSON.stringify(payload),
    });

    const data = await response.json().catch(() => ({}));
    if (!response.ok || data.code !== 0) {
      console.error("[tiktok-click-event]", response.status, data);
    }
    return res.status(200).json({ ok: response.ok && data.code === 0 });
  } catch (e) {
    console.error("[tiktok-click-event]", e);
    return res.status(200).json({ ok: false });
  }
}
