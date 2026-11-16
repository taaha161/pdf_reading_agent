import { PASSWORD_RULES } from "../lib/password";

/** Live password requirements: each rule ticks green as it's met. */
export default function PasswordChecklist({ password, id, showErrors = false }) {
  const value = password || "";
  return (
    <ul className="su-pw-rules" id={id} aria-label="Password requirements">
      {PASSWORD_RULES.map((rule) => {
        const met = rule.test(value);
        const state = met ? "is-met" : showErrors ? "is-missing" : "";
        return (
          <li key={rule.id} className={`su-pw-rule ${state}`.trim()}>
            <span className="su-pw-rule-icon" aria-hidden>
              {met ? (
                <svg width="12" height="12" viewBox="0 0 24 24"><path d="m5 12 5 5 9-10" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" /></svg>
              ) : (
                <svg width="12" height="12" viewBox="0 0 24 24"><circle cx="12" cy="12" r="4" fill="currentColor" /></svg>
              )}
            </span>
            {rule.label}
            <span className="su-sr-only">{met ? " (done)" : " (needed)"}</span>
          </li>
        );
      })}
    </ul>
  );
}
