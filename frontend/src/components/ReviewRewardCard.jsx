import { useEffect, useRef, useState } from "react";
import { submitReviewClaim } from "../api/client";
import { trackEvent } from "../lib/analytics";
import { G2_REVIEW_URL, REVIEW_REWARD_PAGES, TRUSTPILOT_REVIEW_URL } from "../lib/reviews";
import "./FeedbackPrompt.css";
import "./ReviewRewardCard.css";

function StarIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinejoin="round" aria-hidden>
      <path d="m12 3 2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1-4.4-4.3 6.1-.9z" />
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

/**
 * Low-balance offer: 100 pages for a G2 review. Non-modal corner card (same shell as the
 * feedback prompt). Steps: offer -> claim (paste review link/name) -> sent. Granted by hand.
 * `onClose(claimed)`: claimed = a claim was submitted, so the caller can refresh usage.
 */
export default function ReviewRewardCard({ pagesLeft, onClose }) {
  const [step, setStep] = useState("offer"); // offer | claim | sent
  const [proof, setProof] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);
  const cardRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    trackEvent("review_reward_shown", { pages_left: pagesLeft });
    // Shown once per mount; pagesLeft changing mid-view isn't a new impression.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (step === "claim") inputRef.current?.focus();
  }, [step]);

  useEffect(() => {
    const onKey = (e) => {
      if (e.key === "Escape" && !sending && cardRef.current?.contains(document.activeElement)) onClose(step === "sent");
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose, sending, step]);

  const openG2 = () => {
    trackEvent("review_reward_open_g2", { pages_left: pagesLeft });
    setStep("claim");
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const value = proof.trim();
    if (value.length < 2 || sending) return;
    setError(null);
    setSending(true);
    try {
      await submitReviewClaim(value, "g2");
      trackEvent("review_reward_claimed", { pages_left: pagesLeft });
      setStep("sent");
    } catch (err) {
      setError(err.message || "Couldn't send your claim");
    } finally {
      setSending(false);
    }
  };

  return (
    <div ref={cardRef} className="feedback-card" role="dialog" aria-modal="false" aria-labelledby="review-card-title">
      <button
        type="button"
        className="feedback-card-close"
        onClick={() => onClose(step === "sent")}
        disabled={sending}
        aria-label="Close"
      >
        <CloseIcon />
      </button>

      {step === "sent" ? (
        <div className="feedback-card-success" role="status">
          <span className="feedback-card-success-badge">
            <CheckIcon />
          </span>
          <div>
            <h2 id="review-card-title" className="feedback-card-title">Thanks for the review</h2>
            <p className="feedback-card-sub">
              We'll add your {REVIEW_REWARD_PAGES} pages within 1 business day, once we can see your review on G2.
            </p>
          </div>
        </div>
      ) : step === "claim" ? (
        <form onSubmit={handleSubmit} noValidate>
          <div className="feedback-card-head">
            <span className="feedback-card-icon">
              <StarIcon />
            </span>
            <div>
              <p className="feedback-card-eyebrow">Step 2 of 2</p>
              <h2 id="review-card-title" className="feedback-card-title">Claim your {REVIEW_REWARD_PAGES} pages</h2>
            </div>
          </div>
          <div className="feedback-card-more">
            <label htmlFor="review-proof" className="feedback-card-label">
              Your review link, or the name you reviewed under
            </label>
            <input
              id="review-proof"
              ref={inputRef}
              className="feedback-card-textarea review-card-input"
              type="text"
              maxLength={500}
              value={proof}
              onChange={(e) => setProof(e.target.value)}
              disabled={sending}
              aria-describedby="review-proof-hint"
            />
            <p id="review-proof-hint" className="feedback-card-hint">
              G2 checks new reviews before publishing them. We'll match yours and add the pages within 1 business day.{" "}
              <a href={G2_REVIEW_URL} target="_blank" rel="noopener" className="feedback-card-review-link">
                Open G2 again
              </a>
            </p>
          </div>
          {error && (
            <p className="feedback-card-error" role="alert">
              {error}
            </p>
          )}
          <div className="feedback-card-actions">
            <button type="button" className="feedback-card-btn feedback-card-btn--ghost" onClick={() => setStep("offer")} disabled={sending}>
              Back
            </button>
            <button type="submit" className="feedback-card-btn feedback-card-btn--primary" disabled={proof.trim().length < 2 || sending}>
              {sending ? "Sending…" : `Claim ${REVIEW_REWARD_PAGES} pages`}
            </button>
          </div>
        </form>
      ) : (
        <div>
          <div className="feedback-card-head">
            <span className="feedback-card-icon">
              <StarIcon />
            </span>
            <div>
              <p className="feedback-card-eyebrow">
                {pagesLeft.toLocaleString()} {pagesLeft === 1 ? "page" : "pages"} left
              </p>
              <h2 id="review-card-title" className="feedback-card-title">
                Get {REVIEW_REWARD_PAGES} free pages for a G2 review
              </h2>
            </div>
          </div>
          <p className="feedback-card-sub review-card-body">
            Tell others how the scanner works for you. Any honest review counts, good or bad. The pages never expire.
          </p>
          <div className="feedback-card-actions">
            <button type="button" className="feedback-card-btn feedback-card-btn--ghost" onClick={() => onClose(false)}>
              Not now
            </button>
            <a
              href={G2_REVIEW_URL}
              target="_blank"
              rel="noopener"
              className="feedback-card-btn feedback-card-btn--primary review-card-cta"
              onClick={openG2}
            >
              Write a G2 review
            </a>
          </div>
          <p className="feedback-card-hint review-card-foot">
            <button type="button" className="review-card-linkbtn" onClick={() => setStep("claim")}>
              Already reviewed us on G2?
            </button>
          </p>
          {TRUSTPILOT_REVIEW_URL && (
            <p className="feedback-card-hint review-card-foot">
              Prefer Trustpilot?{" "}
              <a href={TRUSTPILOT_REVIEW_URL} target="_blank" rel="noopener" onClick={() => trackEvent("review_trustpilot_click")}>
                Review us there
              </a>
              . Trustpilot reviews don't earn pages.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
