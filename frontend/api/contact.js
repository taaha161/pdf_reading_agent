// Contact form — sends email via Resend when RESEND_API_KEY is set (Vercel env).

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

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function trim(str, max) {
  if (typeof str !== "string") return "";
  const t = str.trim();
  return t.length > max ? t.slice(0, max) : t;
}

export default async function handler(req, res) {
  if (req.method !== "POST") {
    res.setHeader("Allow", "POST");
    return res.status(405).end();
  }

  const parsed = parseBody(req);
  if (parsed === null) {
    return res.status(400).json({ error: "invalid_json" });
  }

  // Honeypot — leave empty (bots often fill hidden fields)
  if (parsed._company) {
    return res.status(200).json({ ok: true });
  }

  const name = trim(parsed.name, 120);
  const email = trim(parsed.email, 254);
  const subject = trim(parsed.subject, 200);
  const message = trim(parsed.message, 10000);

  if (!name || !email || !subject || !message) {
    return res.status(400).json({ error: "missing_fields" });
  }
  if (!EMAIL_RE.test(email)) {
    return res.status(400).json({ error: "invalid_email" });
  }

  const resendKey = process.env.RESEND_API_KEY;
  if (!resendKey) {
    return res.status(503).json({
      error: "not_configured",
      message: "Contact email delivery is not configured on this deployment.",
    });
  }

  const to = process.env.CONTACT_TO_EMAIL || "team@bankstatementscanner.com";
  const from =
    process.env.CONTACT_FROM_EMAIL || "Bank Statement Scanner <onboarding@resend.dev>";

  const text = `Name: ${name}\nEmail: ${email}\n\n${message}`;

  let resendRes;
  try {
    resendRes = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${resendKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        from,
        to: [to],
        subject: `[Contact] ${subject}`,
        reply_to: email,
        text,
      }),
    });
  } catch (e) {
    console.error("contact resend fetch", e);
    return res.status(502).json({ error: "send_failed" });
  }

  if (!resendRes.ok) {
    const errText = await resendRes.text();
    console.error("Resend error", resendRes.status, errText);
    return res.status(502).json({ error: "send_failed" });
  }

  return res.status(200).json({ ok: true });
}
