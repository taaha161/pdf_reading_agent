import { useState } from "react";
import { emailSpreadsheet } from "../api/client";
import "./EmailSpreadsheet.css";

/** Anonymous trial: "Email me the spreadsheet" capture box shown under results. */
export default function EmailSpreadsheet({ jobId, csvContent }) {
  const [email, setEmail] = useState("");
  const [optIn, setOptIn] = useState(false);
  const [sending, setSending] = useState(false);
  const [sentTo, setSentTo] = useState(null);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const address = email.trim();
    if (!address || !jobId || !csvContent || sending) return;
    setError(null);
    setSending(true);
    try {
      await emailSpreadsheet(jobId, address, csvContent, optIn);
      setSentTo(address);
    } catch (err) {
      setError(err.message || "Failed to send email");
    } finally {
      setSending(false);
    }
  };

  if (sentTo) {
    return (
      <div className="email-sheet email-sheet--sent" role="status">
        <p className="email-sheet-title">Sent! Check your inbox.</p>
        <p className="email-sheet-hint">
          Your spreadsheet is on its way to <strong>{sentTo}</strong>. If you don't see it in a minute, check spam.
        </p>
      </div>
    );
  }

  return (
    <form className="email-sheet" onSubmit={handleSubmit}>
      <p className="email-sheet-title">Email me this spreadsheet</p>
      <p className="email-sheet-hint">Get the CSV in your inbox so you have it for later.</p>
      <div className="email-sheet-row">
        <input
          type="email"
          className="email-sheet-input"
          placeholder="you@example.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          disabled={sending}
          aria-label="Email address"
          autoComplete="email"
        />
        <button type="submit" className="email-sheet-button" disabled={sending || !email.trim()}>
          {sending ? "Sending…" : "Send"}
        </button>
      </div>
      <label className="email-sheet-optin">
        <input type="checkbox" checked={optIn} onChange={(e) => setOptIn(e.target.checked)} disabled={sending} />
        <span>Send me occasional tips and product updates</span>
      </label>
      {error && <p className="email-sheet-error" role="alert">{error}</p>}
    </form>
  );
}
