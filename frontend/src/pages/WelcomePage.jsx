import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { supabase } from "../lib/supabase";
import { useAuth } from "../contexts/AuthContext";
import { getPaidSignupSession, setPaidSignupPassword } from "../api/client";
import { clearPendingReferral } from "../lib/referral";
import { PASSWORD_MIN_LENGTH, passwordOk } from "../lib/password";
import { PLAN_PAGES, PLAN_PRICE } from "../lib/pricing";
import PasswordInput from "../components/PasswordInput";
import PasswordChecklist from "../components/PasswordChecklist";
import { GoogleLogo } from "../components/AuthBits";
import SignupLayout, { SecurityList, ValuePanel } from "../components/SignupLayout";

const POLL_MS = 2000;
const POLL_LIMIT = 15; // ~30s, then tell them we'll email a link

function money(cents, currency = "usd") {
  if (cents == null) return null;
  return new Intl.NumberFormat("en-US", { style: "currency", currency: currency.toUpperCase() }).format(cents / 100);
}

function CheckBadge() {
  return (
    <svg width="26" height="26" viewBox="0 0 24 24" aria-hidden>
      <path d="m5 12 5 5 9-10" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

/** Left panel: what they just bought. */
function PlanSummary({ info }) {
  const paid = money(info?.amount_total, info?.currency);
  const d = info?.discount;
  return (
    <ValuePanel
      eyebrow={info ? "Payment received" : "Monthly plan"}
      title={info ? "You're subscribed ✓" : "Finishing your signup"}
      lead={info ? "Your Monthly plan is active. Set up your login and start converting statements." : "We're confirming your payment with Stripe."}
    >
      <div className="su-plan">
        <div className="su-plan-row su-plan-row--head">
          <strong>Monthly plan</strong>
          <strong>${PLAN_PRICE}/mo</strong>
        </div>
        <div className="su-plan-row">
          <span>Pages every month</span>
          <strong>{PLAN_PAGES}</strong>
        </div>
        {d && (
          <div className="su-plan-row">
            <span>Referral code {d.code}</span>
            <strong>
              {d.pct}% off{d.months ? ` for ${d.months} month${d.months === 1 ? "" : "s"}` : ""}
            </strong>
          </div>
        )}
        {paid && (
          <div className="su-plan-row">
            <span>Paid today</span>
            <strong>{paid}</strong>
          </div>
        )}
        <p className="su-plan-note">Stripe has emailed your receipt. Manage or cancel anytime from Account.</p>
      </div>
      <SecurityList />
    </ValuePanel>
  );
}

/**
 * /welcome?session_id=...: Stripe's success page for the paid signup.
 * Confirms the payment (the backend creates the account if the webhook hasn't yet),
 * then lets the buyer set their password once, or continue with Google.
 */
export default function WelcomePage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [params] = useSearchParams();
  const sessionId = params.get("session_id") || "";
  const [info, setInfo] = useState(null); // backend session_status()
  const [polls, setPolls] = useState(0);
  const [password, setPassword] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const timer = useRef(null);

  // Poll until the payment is confirmed and the account exists.
  useEffect(() => {
    if (!sessionId) {
      setInfo({ status: "invalid" });
      return undefined;
    }
    let cancelled = false;
    (async () => {
      const s = await getPaidSignupSession(sessionId).catch(() => ({ status: "error" }));
      if (cancelled) return;
      setInfo(s);
      if ((s.status === "pending" || s.status === "error") && polls < POLL_LIMIT) {
        timer.current = setTimeout(() => setPolls((p) => p + 1), POLL_MS);
      }
      if (s.status === "ready") clearPendingReferral(); // used; don't carry it into another signup
    })();
    return () => {
      cancelled = true;
      clearTimeout(timer.current);
    };
  }, [sessionId, polls]);

  const handleSetPassword = async (e) => {
    e.preventDefault();
    setSubmitted(true);
    setError("");
    if (!passwordOk(password)) {
      document.getElementById("wl-password")?.focus();
      return;
    }
    setSaving(true);
    try {
      const { email } = await setPaidSignupPassword(sessionId, password);
      const { error: signInError } = await supabase.auth.signInWithPassword({ email, password });
      if (signInError) throw signInError;
      navigate("/dashboard", { replace: true });
    } catch (err) {
      setError(err.message || "Couldn't save your password. Please try again.");
      setSaving(false);
    }
  };

  const handleGoogle = async () => {
    setError("");
    const { error: oauthError } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: `${window.location.origin}/dashboard` },
    });
    if (oauthError) setError(oauthError.message);
  };

  const status = info?.status;
  let body;

  if (!info || ((status === "pending" || status === "error") && polls < POLL_LIMIT)) {
    body = (
      <div className="su-state" role="status" aria-live="polite">
        <span className="su-state-icon"><span className="su-spinner" /></span>
        <h2 className="su-title">Confirming your payment…</h2>
        <p className="su-sub">This usually takes a few seconds. Please keep this page open.</p>
      </div>
    );
  } else if (status === "pending" || status === "error") {
    body = (
      <div className="su-state" role="status">
        <span className="su-state-icon su-state-icon--warn" aria-hidden>…</span>
        <h2 className="su-title">Almost there</h2>
        <p className="su-sub">
          Your payment is still being confirmed. As soon as it is, we&apos;ll email you a link to set your password.
          Questions? <Link to="/contact">Contact us</Link>.
        </p>
        <div className="su-state-actions">
          <button type="button" className="su-btn su-btn-primary" onClick={() => setPolls(0)}>Check again</button>
        </div>
      </div>
    );
  } else if (status === "invalid") {
    body = (
      <div className="su-state" role="alert">
        <span className="su-state-icon su-state-icon--warn" aria-hidden>!</span>
        <h2 className="su-title">We couldn&apos;t find that checkout</h2>
        <p className="su-sub">If you were charged, check your email for a link to set your password, or log in.</p>
        <div className="su-state-actions">
          <Link to="/login" className="su-btn su-btn-primary">Log in</Link>
          <Link to="/contact" className="su-btn su-btn-secondary">Contact support</Link>
        </div>
      </div>
    );
  } else if (user) {
    body = (
      <div className="su-state">
        <span className="su-state-icon su-state-icon--success"><CheckBadge /></span>
        <h2 className="su-title">You&apos;re all set</h2>
        <p className="su-sub">Your Monthly plan is active on <strong>{user.email}</strong>.</p>
        <div className="su-state-actions">
          <Link to="/dashboard" className="su-btn su-btn-primary">Go to dashboard →</Link>
        </div>
      </div>
    );
  } else if (info.existing_account) {
    body = (
      <div className="su-state">
        <span className="su-state-icon su-state-icon--success"><CheckBadge /></span>
        <h2 className="su-title">Welcome back</h2>
        <p className="su-sub">
          <strong>{info.email}</strong> already had an account, so we added the Monthly plan to it. Log in to start
          using your {PLAN_PAGES} pages.
        </p>
        <div className="su-state-actions">
          <Link to="/login" className="su-btn su-btn-primary">Log in →</Link>
          <Link to="/forgot-password" className="su-link-btn" style={{ alignSelf: "center" }}>Forgot your password?</Link>
        </div>
      </div>
    );
  } else if (!info.needs_password) {
    body = (
      <div className="su-state">
        <span className="su-state-icon su-state-icon--success"><CheckBadge /></span>
        <h2 className="su-title">Your account is ready</h2>
        <p className="su-sub">Log in with <strong>{info.email}</strong> to start converting statements.</p>
        <div className="su-state-actions">
          <Link to="/login" className="su-btn su-btn-primary">Log in →</Link>
        </div>
      </div>
    );
  } else {
    const showErr = submitted && !passwordOk(password);
    body = (
      <>
        <h2 className="su-title">Set your password</h2>
        <p className="su-sub">
          Last step. Your account is <strong>{info.email}</strong>.
        </p>
        <form onSubmit={handleSetPassword} className="su-form" noValidate>
          {/* Hidden username so password managers save the right login. */}
          <input type="email" value={info.email} autoComplete="username" readOnly hidden />
          <div className="su-field">
            <label className="su-label" htmlFor="wl-password">Password</label>
            <PasswordInput
              id="wl-password"
              className={`su-input${showErr ? " is-invalid" : ""}`}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder={`At least ${PASSWORD_MIN_LENGTH} characters`}
              autoComplete="new-password"
              autoFocus
              aria-invalid={showErr}
              aria-describedby="wl-pw-rules"
            />
            <PasswordChecklist id="wl-pw-rules" password={password} showErrors={submitted} />
          </div>
          {error && <p className="su-alert" role="alert">{error}</p>}
          <button type="submit" className="su-btn su-btn-primary" disabled={saving}>
            {saving ? "Setting up your account…" : "Set password & go to dashboard →"}
          </button>
        </form>
        <div className="su-divider">or</div>
        <button type="button" className="su-btn su-btn-google" onClick={handleGoogle} disabled={saving}>
          <GoogleLogo />
          Continue with Google
        </button>
        <p className="su-legal">Use the Google account for {info.email} so it opens this same account.</p>
      </>
    );
  }

  return (
    <SignupLayout aside={<PlanSummary info={status === "ready" ? info : null} />} headerAction={null}>
      {body}
    </SignupLayout>
  );
}
