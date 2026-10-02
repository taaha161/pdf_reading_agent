import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { emailSpreadsheet } from "../api/client";
import "./EmailSpreadsheet.css";

const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

function FileIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" />
      <path d="M14 3v5h5" />
      <path d="M8.5 13h7M8.5 16.5h7M12 11v8" />
    </svg>
  );
}

function MailIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <rect x="3" y="5" width="18" height="14" rx="2" />
      <path d="m3.5 6.5 8.5 6 8.5-6" />
    </svg>
  );
}

function LockIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <rect x="5" y="11" width="14" height="10" rx="2" />
      <path d="M8 11V8a4 4 0 0 1 8 0v3" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="m5 12.5 4.5 4.5L19 7.5" />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden>
      <path d="M6 6l12 12M18 6 6 18" />
    </svg>
  );
}

/** Anonymous trial: "Email me the spreadsheet" popup shown after a scan. */
export default function EmailSpreadsheet({ jobId, csvContent, transactionCount, onClose }) {
  const [email, setEmail] = useState("");
  const [optIn, setOptIn] = useState(false);
  const [sending, setSending] = useState(false);
  const [sentTo, setSentTo] = useState(null);
  const [error, setError] = useState(null);
  const dialogRef = useRef(null);
  const inputRef = useRef(null);

  // Esc closes; Tab stays inside the dialog; focus returns to the opener on close.
  useEffect(() => {
    const opener = document.activeElement;
    inputRef.current?.focus();
    const onKey = (e) => {
      if (e.key === "Escape" && !sending) onClose();
      if (e.key !== "Tab" || !dialogRef.current) return;
      const focusable = dialogRef.current.querySelectorAll("button:not(:disabled), input:not(:disabled), a[href]");
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      if (opener instanceof HTMLElement) opener.focus();
    };
  }, [onClose, sending]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const address = email.trim();
    if (!EMAIL_RE.test(address)) {
      setError("Please enter a valid email address.");
      inputRef.current?.focus();
      return;
    }
    if (!jobId || !csvContent || sending) return;
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

  const rows = transactionCount === 1 ? "1 transaction" : `${transactionCount ?? 0} transactions`;

  return (
    <>
      <div className="email-sheet-backdrop" onClick={sending ? undefined : onClose} aria-hidden />
      <div
        ref={dialogRef}
        className="email-sheet"
        role="dialog"
        aria-modal="true"
        aria-labelledby="email-sheet-title"
        aria-describedby="email-sheet-desc"
      >
        <button type="button" className="email-sheet-close" onClick={onClose} disabled={sending} aria-label="Close">
          <CloseIcon />
        </button>

        {sentTo ? (
          <div className="email-sheet-body email-sheet-success" role="status">
            <div className="email-sheet-success-badge">
              <CheckIcon />
            </div>
            <h2 id="email-sheet-title" className="email-sheet-title">It's in your inbox</h2>
            <p id="email-sheet-desc" className="email-sheet-desc">
              We sent <strong>statement.csv</strong> to <strong>{sentTo}</strong>. Not there in a minute? Check spam.
            </p>
            <div className="email-sheet-upsell">
              <p className="email-sheet-upsell-title">Converting more than one statement?</p>
              <p className="email-sheet-upsell-text">
                A free account keeps every statement in one place, so you never have to re-upload.
              </p>
              <Link to="/signup" className="email-sheet-cta email-sheet-cta--link" onClick={onClose}>
                Create a free account
              </Link>
            </div>
            <button type="button" className="email-sheet-dismiss" onClick={onClose}>
              Back to my results
            </button>
          </div>
        ) : (
          <>
            <div className="email-sheet-hero" aria-hidden>
              <div className="email-sheet-file">
                <span className="email-sheet-file-icon">
                  <FileIcon />
                </span>
                <span className="email-sheet-file-meta">
                  <span className="email-sheet-file-name">statement.csv</span>
                  <span className="email-sheet-file-rows">{rows} · ready</span>
                </span>
                <span className="email-sheet-file-check">
                  <CheckIcon />
                </span>
              </div>
            </div>

            <form className="email-sheet-body" onSubmit={handleSubmit} noValidate>
              <h2 id="email-sheet-title" className="email-sheet-title">Send this spreadsheet to your inbox</h2>
              <p id="email-sheet-desc" className="email-sheet-desc">
                Your converted statement, ready whenever you need it. Opens in Excel, Google Sheets or Numbers.
              </p>

              <label htmlFor="email-sheet-input" className="email-sheet-label">
                Email address
              </label>
              <div className={`email-sheet-field ${error ? "email-sheet-field--error" : ""}`}>
                <span className="email-sheet-field-icon">
                  <MailIcon />
                </span>
                <input
                  ref={inputRef}
                  id="email-sheet-input"
                  type="email"
                  className="email-sheet-input"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value);
                    if (error) setError(null);
                  }}
                  disabled={sending}
                  autoComplete="email"
                  inputMode="email"
                  aria-invalid={!!error}
                  aria-describedby={error ? "email-sheet-error" : undefined}
                />
              </div>
              {error && (
                <p id="email-sheet-error" className="email-sheet-error" role="alert">
                  {error}
                </p>
              )}

              <button type="submit" className="email-sheet-cta" disabled={sending}>
                {sending ? (
                  <>
                    <span className="email-sheet-spinner" aria-hidden />
                    Sending…
                  </>
                ) : (
                  "Email me the spreadsheet"
                )}
              </button>

              <label className="email-sheet-optin">
                <input type="checkbox" checked={optIn} onChange={(e) => setOptIn(e.target.checked)} disabled={sending} />
                <span>Also send me occasional tips and product updates</span>
              </label>

              <p className="email-sheet-trust">
                <LockIcon />
                No spam. We don't keep a copy of your transactions.
              </p>

              <button type="button" className="email-sheet-dismiss" onClick={onClose} disabled={sending}>
                No thanks
              </button>
            </form>
          </>
        )}
      </div>
    </>
  );
}
