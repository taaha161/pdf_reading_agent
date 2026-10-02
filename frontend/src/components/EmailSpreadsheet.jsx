import { useEffect, useState } from "react";
import { emailSpreadsheet } from "../api/client";
import "./EmailSpreadsheet.css";

/** Anonymous trial: "Email me the spreadsheet" popup shown after a scan. */
export default function EmailSpreadsheet({ jobId, csvContent, onClose }) {
  const [email, setEmail] = useState("");
  const [optIn, setOptIn] = useState(false);
  const [sending, setSending] = useState(false);
  const [sentTo, setSentTo] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const onKey = (e) => {
      if (e.key === "Escape" && !sending) onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose, sending]);

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

  return (
    <>
      <div className="email-sheet-backdrop" onClick={sending ? undefined : onClose} aria-hidden />
      <div className="email-sheet" role="dialog" aria-modal="true" aria-labelledby="email-sheet-title">
        <button type="button" className="email-sheet-close" onClick={onClose} disabled={sending} aria-label="Close">
          ×
        </button>
        {sentTo ? (
          <div role="status">
            <h2 id="email-sheet-title" className="email-sheet-title">Sent! Check your inbox.</h2>
            <p className="email-sheet-hint">
              Your spreadsheet is on its way to <strong>{sentTo}</strong>. If you don't see it in a minute, check spam.
            </p>
            <button type="button" className="email-sheet-button email-sheet-button--full" onClick={onClose}>
              Done
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit}>
            <h2 id="email-sheet-title" className="email-sheet-title">Email me this spreadsheet</h2>
            <p className="email-sheet-hint">Get the CSV in your inbox so you have it for later.</p>
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
              autoFocus
            />
            <label className="email-sheet-optin">
              <input type="checkbox" checked={optIn} onChange={(e) => setOptIn(e.target.checked)} disabled={sending} />
              <span>Send me occasional tips and product updates</span>
            </label>
            {error && <p className="email-sheet-error" role="alert">{error}</p>}
            <div className="email-sheet-actions">
              <button type="button" className="email-sheet-button secondary" onClick={onClose} disabled={sending}>
                No thanks
              </button>
              <button type="submit" className="email-sheet-button" disabled={sending || !email.trim()}>
                {sending ? "Sending…" : "Send"}
              </button>
            </div>
          </form>
        )}
      </div>
    </>
  );
}
