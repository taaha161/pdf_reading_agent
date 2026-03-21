// Server-side TikTok Events API (v1.3) for email signup — keeps the access token off the client.
// Set TIKTOK_EVENTS_ACCESS_TOKEN in Vercel (Events Manager → your pixel → Generate access token).
// Optional: TIKTOK_PIXEL_CODE (defaults to the pixel in index.html).

import crypto from "node:crypto";

const ENDPOINT = "https://business-api.tiktok.com/open_api/v1.3/event/track/";
const DEFAULT_PIXEL = "D6VG41RC77UCSLHQUEDG";

function sha256Hex(value) {
  return crypto.createHash("sha256").update(value.toLowerCase().trim(), "utf8").digest("hex");
}

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

  const email = typeof body.email === "string" ? body.email.trim() : "";
  if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    return res.status(400).json({ ok: false, error: "invalid_email" });
  }

  const pixelCode = process.env.TIKTOK_PIXEL_CODE || DEFAULT_PIXEL;
  const url = typeof body.url === "string" ? body.url : "";
  const referrer = typeof body.referrer === "string" ? body.referrer : "";
  const ttclid = typeof body.ttclid === "string" && body.ttclid.trim() ? body.ttclid.trim() : undefined;
  const ttp = typeof body.ttp === "string" && body.ttp.trim() ? body.ttp.trim() : undefined;

  const userAgent = req.headers["user-agent"] || "";
  const ip = clientIp(req);
  const eventId = crypto.randomUUID();

  const context = {
    ip,
    user_agent: userAgent,
    page: {
      ...(url && { url }),
      ...(referrer && { referrer }),
    },
    user: {
      email: sha256Hex(email),
      ...(ttp && { ttp }),
    },
    ...(ttclid && { ad: { callback: ttclid } }),
  };

  const payload = {
    event_source: "web",
    event_source_id: pixelCode,
    data: [
      {
        event: "CompleteRegistration",
        event_time: Math.floor(Date.now() / 1000),
        event_id: eventId,
        context,
        properties: {
          content_type: "registration",
          content_name: "Account signup",
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
      console.error("[tiktok-signup-event]", response.status, data);
    }
    return res.status(200).json({ ok: response.ok && data.code === 0 });
  } catch (e) {
    console.error("[tiktok-signup-event]", e);
    return res.status(200).json({ ok: false });
  }
}
