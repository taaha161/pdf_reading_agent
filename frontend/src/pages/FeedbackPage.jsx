import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { submitFeedback } from "../api/client";
import { useAuth } from "../contexts/AuthContext";
import { LANDING_URL } from "../lib/seo";
import "./ContactPage.css";
import "../components/FeedbackPrompt.css";

const RATINGS = [1, 2, 3, 4, 5];
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** Comment prompt adapts to the score so the question is answerable. */
function commentLabel(rating) {
  if (rating == null) return "Anything you'd like to tell us?";
  if (rating <= 2) return "What went wrong?";
  if (rating <= 4) return "What would make it better?";
  return "What do you like most?";
}

/**
 * Standalone feedback form at /feedback, linkable from emails. Posts to the same
 * /api/feedback endpoint as the in-app prompt. Optional ?job=<uuid> ties it to a scan.
 */
export default function FeedbackPage() {
  const [searchParams] = useSearchParams();
  const jobParam = searchParams.get("job") || "";
  const jobId = UUID_RE.test(jobParam) ? jobParam : null;
  const { user } = useAuth();
  const isLoggedIn = !!user;

  const [rating, setRating] = useState(null);
  const [comment, setComment] = useState("");
  const [contactOk, setContactOk] = useState(true);
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState(null);

  const sending = status === "sending";
  const canSubmit = (rating != null || comment.trim() !== "") && !sending;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!canSubmit) return;
    setError(null);
    setStatus("sending");
    try {
      await submitFeedback({ jobId, rating, comment: comment.trim(), contactOk: isLoggedIn && contactOk });
      setStatus("success");
      try {
        (window.dataLayer = window.dataLayer || []).push({ event: "feedback_page_submit", rating });
      } catch {
        /* ignore */
      }
    } catch (err) {
      setError(err.message || "Couldn't send feedback");
      setStatus("idle");
    }
  };

  const header = (
    <header className="contact-page-header">
      <a href={LANDING_URL} className="contact-back">
        ← Back to home
      </a>
    </header>
  );

  if (status === "success") {
    return (
      <div className="contact-page">
        {header}
        <main className="contact-main">
          <h1 className="contact-hero-title">Thanks for the feedback</h1>
          <p className="contact-hero-subtitle">We read every response, and it goes straight into what we fix next.</p>
          <a href="/scanner">Back to the scanner</a>
        </main>
      </div>
    );
  }

  return (
    <div className="contact-page">
      {header}
      <main className="contact-main">
        <h1 className="contact-hero-title">Share your feedback</h1>
        <p className="contact-hero-subtitle">
          How is Bank Statement Scanner working for you? It takes under a minute, and every answer is read by the team.
        </p>

        {error && (
          <p className="contact-message contact-message--error" role="alert">
            {error}
          </p>
        )}

        <form className="contact-form" onSubmit={handleSubmit} noValidate>
          <fieldset className="feedback-scale" disabled={sending}>
            <legend className="contact-field-legend">How would you rate it overall?</legend>
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

          <div className="contact-field">
            <label htmlFor="feedback-page-comment">{commentLabel(rating)}</label>
            <textarea
              id="feedback-page-comment"
              rows={6}
              maxLength={2000}
              placeholder="Which bank or statement, what worked, what didn't, what you'd like us to add…"
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              disabled={sending}
            />
          </div>

          {isLoggedIn && (
            <label className="feedback-card-contact">
              <input type="checkbox" checked={contactOk} onChange={(e) => setContactOk(e.target.checked)} disabled={sending} />
              <span>You can email me about this</span>
            </label>
          )}

          <button type="submit" className="contact-submit" disabled={!canSubmit}>
            {sending ? "Sending…" : "Send feedback"}
          </button>
        </form>
      </main>
    </div>
  );
}
