import { useEffect, useState } from "react";
import { lookupReferral } from "../api/client";
import { clearPendingReferral, describeDiscount, getPendingReferral, normalizeReferralCode } from "../lib/referral";

/**
 * Optional affiliate code, collapsed behind "Have a referral code?".
 * Opens (and applies) itself when the visitor came through a ?ref= link.
 * Reports changes through onChange({ applied: {code, discount} | null, pendingText }).
 */
export default function ReferralCodeField({ onChange }) {
  const [open, setOpen] = useState(false);
  const [text, setText] = useState("");
  const [applied, setApplied] = useState(null); // { code, discount }
  const [status, setStatus] = useState("idle"); // idle | checking | invalid | offline

  useEffect(() => {
    onChange?.({ applied, pendingText: applied ? "" : text.trim() });
  }, [applied, text, onChange]);

  const apply = async (raw = text) => {
    const code = normalizeReferralCode(raw);
    if (!code) {
      setStatus(raw.trim() ? "invalid" : "idle");
      return;
    }
    setStatus("checking");
    const info = await lookupReferral(code);
    if (info?.valid) {
      setApplied({ code, discount: info.discount ?? null });
      setText(code);
      setStatus("idle");
    } else {
      // null = the check itself failed (network/server), not a bad code.
      setStatus(info === null ? "offline" : "invalid");
    }
  };

  // Came in through an affiliate link: open and apply without a click.
  useEffect(() => {
    const pending = getPendingReferral();
    if (pending) {
      setOpen(true);
      setText(pending);
      apply(pending);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const remove = () => {
    setApplied(null);
    setText("");
    setStatus("idle");
    clearPendingReferral(); // so a ?ref= code isn't claimed on first sign-in
  };

  if (!open) {
    return (
      <button type="button" className="su-link-btn su-referral-toggle" onClick={() => setOpen(true)} aria-expanded="false">
        <svg width="14" height="14" viewBox="0 0 24 24" aria-hidden><path d="M12 5v14M5 12h14" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" /></svg>
        Have a referral code?
      </button>
    );
  }

  return (
    <div className="su-field su-referral">
      <label className="su-label" htmlFor="su-referral-input">
        Referral code <span className="su-optional">optional</span>
      </label>
      <div className="su-referral-row">
        <input
          id="su-referral-input"
          type="text"
          className={`su-input${applied ? " is-applied" : ""}${status === "invalid" ? " is-invalid" : ""}`}
          value={text}
          onChange={(e) => {
            setText(e.target.value);
            if (status !== "idle" && status !== "checking") setStatus("idle");
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault(); // apply the code, don't submit the form
              if (!applied) apply();
            }
          }}
          placeholder="e.g. jane"
          maxLength={32}
          readOnly={!!applied}
          autoComplete="off"
          autoCapitalize="none"
          spellCheck={false}
          aria-describedby="su-referral-status"
          aria-invalid={status === "invalid"}
          autoFocus={!applied && !getPendingReferral()}
        />
        {applied ? (
          <button type="button" className="su-chip-btn su-chip-btn--ghost" onClick={remove}>Remove</button>
        ) : (
          <button
            type="button"
            className="su-chip-btn"
            onClick={() => apply()}
            disabled={!text.trim() || status === "checking"}
          >
            {status === "checking" ? "Checking…" : "Apply"}
          </button>
        )}
      </div>
      <p id="su-referral-status" className={`su-hint${applied ? " is-success" : ""}${status === "invalid" || status === "offline" ? " is-error" : ""}`} aria-live="polite">
        {status === "invalid" && "We don't recognize that code. Check it, or leave it blank."}
        {status === "offline" && "Couldn't check the code right now. Try Apply again in a moment."}
        {applied && (applied.discount ? `✓ Applied: ${describeDiscount(applied.discount)}` : "✓ Code applied")}
      </p>
    </div>
  );
}
