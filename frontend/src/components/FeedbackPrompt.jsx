import { useEffect, useRef, useState } from "react";
import { submitFeedback } from "../api/client";
import "./FeedbackPrompt.css";

const RATINGS = [1, 2, 3, 4, 5];
const SUCCESS_CLOSE_MS = 3500;
/** Public review profile (Trustpilot/G2). Unset = no review ask. Happy raters (4–5) get the link. */
const REVIEW_URL = import.meta.env.VITE_REVIEW_URL || "";
const REVIEW_MIN_RATING = 4;

function MessageIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
      <path d="M8 9h8M8 13h5" />
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

/** Follow-up question adapts to the score so the comment box asks something answerable. */
function followUp(rating) {
  if (rating <= 2) return { label: "What went wrong?", hint: "Missing or wrong transactions? Tell us which bank, so we can fix it." };
  if (rating <= 4) return { label: "What would make it better?", hint: null };
  return { label: "What do you like most?", hint: null };
}

/**
 * Optional feedback card, prompted after a user's second scan. Non-modal: it sits in the
 * corner without blocking the results, never takes focus on open, and closes with Esc,
 * the X or "Not now".
 */
export default function FeedbackPrompt({ jobId, isLoggedIn, onClose }) {
  const [rating, setRating] = useState(null);
  const [comment, setComment] = useState("");
  const [contactOk, setContactOk] = useState(false);
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState(null);
  const cardRef = useRef(null);

  // Esc closes, but only when focus is inside the card so it never hijacks other UI.
  useEffect(() => {
    const onKey = (e) => {
      if (e.key === "Escape" && !sending && cardRef.current?.contains(document.activeElement)) onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose, sending]);

  const askForReview = sent && !!REVIEW_URL && rating != null && rating >= REVIEW_MIN_RATING;

  useEffect(() => {
    // Keep the card open when it's asking for a public review; it closes via X or the link.
    if (!sent || askForReview) return;
    const timer = setTimeout(onClose, SUCCESS_CLOSE_MS);
    return () => clearTimeout(timer);
  }, [sent, askForReview, onClose]);

  const canSubmit = (rating != null || comment.trim() !== "") && !sending;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!canSubmit) return;
    setError(null);
    setSending(true);
    try {
      await submitFeedback({ jobId, rating, comment: comment.trim(), contactOk: isLoggedIn && contactOk });
      setSent(true);
    } catch (err) {
      setError(err.message || "Couldn't send feedback");
    } finally {
      setSending(false);
    }
  };

  const question = rating != null ? followUp(rating) : null;

  return (
    <div
      ref={cardRef}
      className="feedback-card"
      role="dialog"
      aria-modal="false"
      aria-labelledby="feedback-card-title"
    >
      <button type="button" className="feedback-card-close" onClick={onClose} disabled={sending} aria-label="Close feedback">
        <CloseIcon />
      </button>

      {sent ? (
        <div className="feedback-card-success" role="status">
          <span className="feedback-card-success-badge">
            <CheckIcon />
          </span>
          <div>
            <h2 id="feedback-card-title" className="feedback-card-title">Thanks, that helps</h2>
            <p className="feedback-card-sub">We read every response.</p>
            {askForReview && (
              <p className="feedback-card-sub">
                Glad it's working. Would you share that in a quick public review? It helps other accountants find us.{" "}
                <a
                  href={REVIEW_URL}
                  target="_blank"
                  rel="noopener"
                  className="feedback-card-review-link"
                  onClick={() => {
                    try {
                      (window.dataLayer = window.dataLayer || []).push({ event: "review_click", rating });
                    } catch {
                      /* ignore */
                    }
                    onClose();
                  }}
                >
                  Leave a review →
                </a>
              </p>
            )}
          </div>
        </div>
      ) : (
        <form onSubmit={handleSubmit} noValidate>
          <div className="feedback-card-head">
            <span className="feedback-card-icon">
              <MessageIcon />
            </span>
            <div>
              <p className="feedback-card-eyebrow">Optional · takes 10 seconds</p>
              <h2 id="feedback-card-title" className="feedback-card-title">How's the scanner working for you?</h2>
            </div>
          </div>

          <fieldset className="feedback-scale" disabled={sending}>
            <legend className="feedback-sr-only">Rate the scanner from 1 (not great) to 5 (excellent)</legend>
            <div className="feedback-scale-track">
              {RATINGS.map((n) => (
                <label key={n} className={`feedback-scale-option ${rating === n ? "is-active" : ""}`}>
                  <input type="radio" name="feedback-rating" value={n} checked={rating === n} onChange={() => setRating(n)} />
                  {n}
                </label>
              ))}
            </div>
            <div className="feedback-scale-ends" aria-hidden>
              <span>Not great</span>
              <span>Excellent</span>
            </div>
          </fieldset>

          {question && (
            <div className="feedback-card-more">
              <label htmlFor="feedback-comment" className="feedback-card-label">
                {question.label} <span className="feedback-card-optional">(optional)</span>
              </label>
              <textarea
                id="feedback-comment"
                className="feedback-card-textarea"
                rows={3}
                maxLength={2000}
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                disabled={sending}
                aria-describedby={question.hint ? "feedback-comment-hint" : undefined}
              />
              {question.hint && (
                <p id="feedback-comment-hint" className="feedback-card-hint">
                  {question.hint}
                </p>
              )}
              {isLoggedIn && (
                <label className="feedback-card-contact">
                  <input type="checkbox" checked={contactOk} onChange={(e) => setContactOk(e.target.checked)} disabled={sending} />
                  <span>You can email me about this</span>
                </label>
              )}
            </div>
          )}

          {error && (
            <p className="feedback-card-error" role="alert">
              {error}
            </p>
          )}

          <div className="feedback-card-actions">
            <button type="button" className="feedback-card-btn feedback-card-btn--ghost" onClick={onClose} disabled={sending}>
              Not now
            </button>
            <button type="submit" className="feedback-card-btn feedback-card-btn--primary" disabled={!canSubmit}>
              {sending ? "Sending…" : "Send feedback"}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
