import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import "./ContactPage.css";

const SUBJECT_OPTIONS = [
  { value: "General question", label: "General question" },
  { value: "Billing & account", label: "Billing & account" },
  { value: "Technical / product issue", label: "Technical / product issue" },
  { value: "Partnership or press", label: "Partnership or press" },
];

const TOPIC_DEFAULT = {
  general: "General question",
  billing: "Billing & account",
  technical: "Technical / product issue",
  partnership: "Partnership or press",
  sales: "Partnership or press",
};

function contactApiUrl() {
  const base = import.meta.env.BASE_URL || "/";
  return `${base.replace(/\/$/, "")}/api/contact`;
}

function buildMailto({ email, subject, message, name }) {
  const body = `Name: ${name}\nEmail: ${email}\n\n${message}`;
  return `mailto:team@bankstatementscanner.com?subject=${encodeURIComponent(`[Contact] ${subject}`)}&body=${encodeURIComponent(body)}`;
}

export default function ContactPage() {
  const [searchParams] = useSearchParams();
  const topicKey = (searchParams.get("topic") || "").toLowerCase();

  const initialSubject = useMemo(() => {
    return TOPIC_DEFAULT[topicKey] || SUBJECT_OPTIONS[0].value;
  }, [topicKey]);

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [subject, setSubject] = useState(initialSubject);
  const [message, setMessage] = useState("");

  useEffect(() => {
    setSubject(initialSubject);
  }, [initialSubject]);
  const [honeypot, setHoneypot] = useState("");
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setStatus("sending");

    try {
      const res = await fetch(contactApiUrl(), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name,
          email,
          subject,
          message,
          _company: honeypot,
        }),
      });

      const data = await res.json().catch(() => ({}));

      if (res.ok && data.ok) {
        setStatus("success");
        setName("");
        setEmail("");
        setMessage("");
        return;
      }

      if (res.status === 503 && data.error === "not_configured") {
        setError({ type: "not_configured", mailto: buildMailto({ name, email, subject, message }) });
        setStatus("idle");
        return;
      }

      if (res.status === 400) {
        setError({ type: "validation", code: data.error });
        setStatus("idle");
        return;
      }

      setError({ type: "generic" });
      setStatus("idle");
    } catch {
      setError({
        type: "network",
        mailto: buildMailto({ name, email, subject, message }),
      });
      setStatus("idle");
    }
  };

  if (status === "success") {
    return (
      <div className="contact-page">
        <header className="contact-page-header">
          <Link to="/" className="contact-back">
            ← Back to home
          </Link>
        </header>
        <main className="contact-main">
          <h1 className="contact-hero-title">Message sent</h1>
          <p className="contact-hero-subtitle">
            Thanks for reaching out—we&apos;ll reply to the email address you provided as soon as we can.
          </p>
          <Link to="/">Return to home</Link>
        </main>
      </div>
    );
  }

  return (
    <div className="contact-page">
      <header className="contact-page-header">
        <Link to="/" className="contact-back">
          ← Back to home
        </Link>
      </header>
      <main className="contact-main">
        <h1 className="contact-hero-title">Help Center</h1>
        <p className="contact-hero-subtitle">
          Questions about Bank Statement Scanner, your account, or a technical issue? Send us a message—we read every
          submission.
        </p>

        {error?.type === "validation" && (
          <p className="contact-message contact-message--error" role="alert">
            {error.code === "invalid_email"
              ? "Please enter a valid email address."
              : "Please fill in your name, email, subject, and message."}
          </p>
        )}
        {error?.type === "generic" && (
          <p className="contact-message contact-message--error" role="alert">
            We couldn&apos;t send your message just now. Please try again in a moment.
          </p>
        )}

        <form className="contact-form" onSubmit={handleSubmit} noValidate>
          <div className="contact-field contact-honeypot" aria-hidden="true">
            <label htmlFor="contact-company">Company</label>
            <input
              id="contact-company"
              name="company"
              type="text"
              tabIndex={-1}
              autoComplete="off"
              value={honeypot}
              onChange={(e) => setHoneypot(e.target.value)}
            />
          </div>

          <div className="contact-field">
            <label htmlFor="contact-name">Name</label>
            <input
              id="contact-name"
              name="name"
              type="text"
              required
              autoComplete="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>

          <div className="contact-field">
            <label htmlFor="contact-email">Email</label>
            <input
              id="contact-email"
              name="email"
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>

          <div className="contact-field">
            <label htmlFor="contact-subject">Topic</label>
            <select
              id="contact-subject"
              name="subject"
              required
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
            >
              {SUBJECT_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          <div className="contact-field">
            <label htmlFor="contact-message">Message</label>
            <textarea
              id="contact-message"
              name="message"
              required
              rows={6}
              placeholder="Describe your question or issue…"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
            />
          </div>

          <button type="submit" className="contact-submit" disabled={status === "sending"}>
            {status === "sending" ? "Sending…" : "Send message"}
          </button>
        </form>

        {(error?.type === "not_configured" || error?.type === "network") && error.mailto && (
          <div className="contact-fallback">
            <p style={{ margin: "0 0 0.75rem" }}>
              You can also email us directly—your draft is prefilled when you open the link below.
            </p>
            <a href={error.mailto}>Open in email app</a>
          </div>
        )}
      </main>
    </div>
  );
}
