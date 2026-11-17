import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate, useLocation, useSearchParams } from "react-router-dom";
import { supabase } from "../lib/supabase";
import { sendTikTokSignupEvent } from "../lib/tiktokSignupEvent";
import { trackSignup } from "../lib/trackSignup";
import { useAuth } from "../contexts/AuthContext";
import LogoMark from "../components/LogoMark";
import "./AuthPage.css";
import PasswordInput from "../components/PasswordInput";
import PasswordChecklist from "../components/PasswordChecklist";
import ReferralCodeField from "../components/ReferralCodeField";
import SignupLayout, { BenefitList, SecurityList, ValuePanel } from "../components/SignupLayout";
import { GoogleLogo } from "../components/AuthBits";
import { claimOfferForUser } from "../lib/offer";
import { getAttribution } from "../lib/attribution";
import { setPendingReferral } from "../lib/referral";
import { PASSWORD_MIN_LENGTH, passwordOk } from "../lib/password";
import { FREE_ANON_PAGES, FREE_SIGNUP_DAYS, FREE_SIGNUP_PAGES, PLAN_PAGES, PLAN_PRICE } from "../lib/pricing";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const RESEND_COOLDOWN_S = 30;

function MailIcon() {
  return (
    <svg width="26" height="26" viewBox="0 0 24 24" aria-hidden>
      <path d="M3 6h18v12H3z M3 7l9 6 9-6" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
    </svg>
  );
}

/** Left panel for /signup: normal, or after the anonymous free pages ran out. */
function SignupAside({ trialExhausted }) {
  if (trialExhausted) {
    return (
      <ValuePanel
        eyebrow={`You've used your ${FREE_ANON_PAGES} guest pages`}
        title={`Keep going with ${FREE_SIGNUP_PAGES} more pages, free`}
        lead={`Create a free account and your next ${FREE_SIGNUP_PAGES} pages are on us for ${FREE_SIGNUP_DAYS} days. No credit card.`}
      >
        <ol className="su-meter" aria-label="Your free pages">
          <li><strong>{FREE_ANON_PAGES} pages</strong><span>Guest limit, used</span></li>
          <li className="is-free"><strong>+{FREE_SIGNUP_PAGES} pages</strong><span>Free with an account</span></li>
        </ol>
        <SecurityList />
      </ValuePanel>
    );
  }
  return (
    <ValuePanel
      eyebrow="Free account"
      title="Turn bank statements into clean spreadsheets"
      lead="Upload a PDF statement from any bank and get categorized transactions in Excel or CSV in seconds."
    >
      <BenefitList
        items={[
          "Works with any bank, digital or scanned PDFs",
          "AI categorizes every transaction for you",
          "Ask your statements questions in plain English",
        ]}
      />
      <SecurityList />
    </ValuePanel>
  );
}

export default function AuthPage({ mode: initialMode = "login" }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuth();
  const [searchParams] = useSearchParams();
  const fromLoc = location.state?.from;
  const from = fromLoc?.pathname ? `${fromLoc.pathname}${fromLoc.search || ""}` : "/dashboard";
  const notice = location.state?.notice;
  // Redirected from the scanner after the anonymous free pages ran out.
  const trialExhausted = location.state?.reason === "trial-exhausted";
  const modeFromQuery = searchParams.get("mode"); // e.g. /login?mode=signup
  const mode = modeFromQuery === "signup" || modeFromQuery === "login" || modeFromQuery === "forgot" ? modeFromQuery : initialMode;

  const [view, setView] = useState(mode); // "login" | "signup" | "forgot-password"
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  // Referral code field state: { applied: {code, discount} | null, pendingText }.
  const [referral, setReferral] = useState({ applied: null, pendingText: "" });
  const onReferralChange = useCallback((r) => setReferral(r), []);
  // Signup field errors, shown after the first submit attempt.
  const [submitted, setSubmitted] = useState(false);
  const [pwFocused, setPwFocused] = useState(false);
  const [resendIn, setResendIn] = useState(0);
  const resendTimer = useRef(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState({ type: "", text: "" });
  const [signupSuccess, setSignupSuccess] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);

  useEffect(() => {
    setView(mode);
    // e.g. redirected here from the scanner after using the free pages
    // (the trial-exhausted signup view has its own panel instead)
    setMessage(notice && !trialExhausted ? { type: "success", text: notice } : { type: "", text: "" });
    setSignupSuccess(false);
    setSubmitted(false);
  }, [mode, notice, trialExhausted]);

  // Redirect if already logged in (skip on reset-password; that page handles its own logic)
  useEffect(() => {
    if (user && view !== "reset-password") {
      navigate(from, { replace: true });
    }
  }, [user, view, navigate, from]);

  useEffect(() => () => clearInterval(resendTimer.current), []);

  const setError = (text) => setMessage({ type: "error", text });
  const setSuccess = (text) => setMessage({ type: "success", text });
  const clearMessage = () => setMessage({ type: "", text: "" });

  const handleSocialLogin = async (provider) => {
    setLoading(true);
    clearMessage();
    // OAuth accounts don't exist yet: keep the referral for the first sign-in.
    if (view === "signup" && referral.applied) setPendingReferral(referral.applied.code);
    try {
      const { error } = await supabase.auth.signInWithOAuth({ provider });
      if (error) setError(error.message);
    } catch (e) {
      setError(e.message || "Sign in failed");
    } finally {
      setLoading(false);
    }
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    clearMessage();
    try {
      const { error } = await supabase.auth.signInWithPassword({ email: email.trim(), password });
      if (error) throw error;
      navigate(from, { replace: true });
    } catch (err) {
      setError(err.message || "Invalid email or password");
    } finally {
      setLoading(false);
    }
  };

  const signupErrors = {
    name: !fullName.trim() ? "Enter your name" : "",
    email: !EMAIL_RE.test(email.trim()) ? "Enter a valid email address" : "",
    password: !passwordOk(password) ? "Password doesn't meet the requirements below" : "",
    referral: referral.pendingText ? "Click Apply to use this code, or clear the field" : "",
  };

  const startResendCooldown = () => {
    setResendIn(RESEND_COOLDOWN_S);
    clearInterval(resendTimer.current);
    resendTimer.current = setInterval(() => {
      setResendIn((s) => {
        if (s <= 1) clearInterval(resendTimer.current);
        return Math.max(0, s - 1);
      });
    }, 1000);
  };

  const handleSignUp = async (e) => {
    e.preventDefault();
    clearMessage();
    setSubmitted(true);
    const firstError = Object.values(signupErrors).find(Boolean);
    if (firstError) {
      // Move focus to the first field with a problem.
      const order = [["name", "su-name"], ["email", "su-email"], ["password", "su-password"], ["referral", "su-referral-input"]];
      const bad = order.find(([k]) => signupErrors[k]);
      document.getElementById(bad?.[1])?.focus();
      return;
    }
    setLoading(true);
    try {
      const { data: signUpData, error } = await supabase.auth.signUp({
        email: email.trim(),
        password,
        options: {
          // attribution: which ad campaign (if any) brought this signup in.
          data: {
            full_name: fullName.trim(),
            attribution: getAttribution() ?? undefined,
            signup_plan: "trial",
            referral_code: referral.applied?.code ?? undefined, // claimed server-side on first sign-in
          },
        },
      });
      if (error) throw error;
      sendTikTokSignupEvent({ email: email.trim() });
      trackSignup({ method: "email", userId: signUpData?.user?.id });
      // Bind the ad offer now: the confirmation link may open in another tab.
      claimOfferForUser(signUpData?.user);
      setSignupSuccess(true);
      startResendCooldown();
    } catch (err) {
      setError(err.message || "Sign up failed");
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    clearMessage();
    try {
      const { error } = await supabase.auth.resend({ type: "signup", email: email.trim() });
      if (error) throw error;
      setSuccess("Sent again. Check your inbox and spam folder.");
      startResendCooldown();
    } catch (err) {
      setError(err.message || "Couldn't resend the email. Try again in a minute.");
    }
  };

  const handleForgotPassword = async (e) => {
    e.preventDefault();
    if (!email.trim()) {
      setError("Enter your email address");
      return;
    }
    setLoading(true);
    clearMessage();
    try {
      const redirectTo = `${window.location.origin}/reset-password`;
      const { error } = await supabase.auth.resetPasswordForEmail(email.trim(), { redirectTo });
      if (error) throw error;
      setSuccess("Check your email for a link to reset your password.");
    } catch (err) {
      setError(err.message || "Failed to send reset email");
    } finally {
      setLoading(false);
    }
  };

  // Already logged in
  if (user && view !== "reset-password") {
    return null; // redirect runs in useEffect
  }

  // --- Forgot password view ---
  if (view === "forgot-password" || mode === "forgot") {
    return (
      <div className="auth-page">
        <div className="auth-card">
          <h1 className="auth-title">Reset password</h1>
          <p className="auth-description">
            Enter your email and we&apos;ll send you a link to reset your password.
          </p>
          <form onSubmit={handleForgotPassword} className="auth-form">
            <label className="auth-label">Email</label>
            <input
              type="email"
              className="auth-input"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              required
              autoComplete="email"
            />
            <button type="submit" className="auth-btn auth-btn-primary" disabled={loading}>
              {loading ? "Sending…" : "Send reset link"}
            </button>
          </form>
          {message.text && (
            <p className={`auth-message auth-message-${message.type}`} role="alert">
              {message.text}
            </p>
          )}
          <p className="auth-footer">
            <Link to="/login" className="auth-link-inline">← Back to log in</Link>
          </p>
          <Link to="/" className="auth-back">← Back to home</Link>
        </div>
      </div>
    );
  }

  // --- Sign up view (free account; the paid plan signs up through /subscribe) ---
  if (view === "signup") {
    const showErr = (k) => submitted && signupErrors[k];
    return (
      <SignupLayout aside={<SignupAside trialExhausted={trialExhausted} />}>
        {signupSuccess ? (
          <div className="su-state" role="status">
            <span className="su-state-icon"><MailIcon /></span>
            <h2 className="su-title">Check your inbox</h2>
            <p className="su-sub">
              We sent a confirmation link to <strong>{email.trim()}</strong>. Click it to activate your account and
              get your {FREE_SIGNUP_PAGES} free pages.
            </p>
            <div className="su-state-actions">
              <Link to="/login" className="su-btn su-btn-primary">I&apos;ve confirmed, log in</Link>
              <button type="button" className="su-btn su-btn-secondary" onClick={handleResend} disabled={resendIn > 0}>
                {resendIn > 0 ? `Resend email in ${resendIn}s` : "Resend email"}
              </button>
              <button type="button" className="su-link-btn" style={{ alignSelf: "center" }} onClick={() => { setSignupSuccess(false); clearMessage(); }}>
                Wrong email? Go back
              </button>
            </div>
            {message.text && (
              <p className={message.type === "error" ? "su-alert" : "su-alert su-alert--info"} role="alert" style={{ marginTop: "1rem" }}>
                {message.text}
              </p>
            )}
          </div>
        ) : (
          <>
            <h2 className="su-title">Create your free account</h2>
            <p className="su-sub">
              <strong>{FREE_SIGNUP_PAGES} pages free</strong> for {FREE_SIGNUP_DAYS} days. No credit card needed.
            </p>

            <button type="button" className="su-btn su-btn-google" onClick={() => handleSocialLogin("google")} disabled={loading}>
              <GoogleLogo />
              Continue with Google
            </button>
            <div className="su-divider">or sign up with email</div>

            <form onSubmit={handleSignUp} className="su-form" noValidate>
              <div className="su-field">
                <label className="su-label" htmlFor="su-name">Full name</label>
                <input
                  id="su-name"
                  type="text"
                  className={`su-input${showErr("name") ? " is-invalid" : ""}`}
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Jane Doe"
                  autoComplete="name"
                  aria-invalid={!!showErr("name")}
                  aria-describedby="su-name-err"
                />
                <p id="su-name-err" className="su-hint is-error">{showErr("name")}</p>
              </div>

              <div className="su-field">
                <label className="su-label" htmlFor="su-email">Email</label>
                <input
                  id="su-email"
                  type="email"
                  className={`su-input${showErr("email") ? " is-invalid" : ""}`}
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@company.com"
                  autoComplete="email"
                  inputMode="email"
                  aria-invalid={!!showErr("email")}
                  aria-describedby="su-email-err"
                />
                <p id="su-email-err" className="su-hint is-error">{showErr("email")}</p>
              </div>

              <div className="su-field">
                <label className="su-label" htmlFor="su-password">Password</label>
                <PasswordInput
                  id="su-password"
                  className={`su-input${showErr("password") ? " is-invalid" : ""}`}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  onFocus={() => setPwFocused(true)}
                  placeholder={`At least ${PASSWORD_MIN_LENGTH} characters`}
                  autoComplete="new-password"
                  aria-invalid={!!showErr("password")}
                  aria-describedby="su-pw-rules"
                />
                {(pwFocused || password || submitted) && (
                  <PasswordChecklist id="su-pw-rules" password={password} showErrors={submitted} />
                )}
              </div>

              <ReferralCodeField onChange={onReferralChange} />
              {showErr("referral") && <p className="su-hint is-error" role="alert">{signupErrors.referral}</p>}

              {message.text && (
                <p className={message.type === "error" ? "su-alert" : "su-alert su-alert--info"} role="alert">
                  {message.text}
                </p>
              )}

              <button type="submit" className="su-btn su-btn-primary" disabled={loading}>
                {loading ? "Creating your account…" : "Create free account →"}
              </button>
            </form>

            <p className="su-legal">
              By creating an account you agree to our{" "}
              <Link to="/terms-of-service">Terms of Service</Link> and <Link to="/privacy-policy">Privacy Policy</Link>.
            </p>
            <p className="su-alt">
              Need more pages? <Link to="/subscribe">Get the Monthly plan: {PLAN_PAGES} pages/mo for ${PLAN_PRICE} →</Link>
            </p>
          </>
        )}
      </SignupLayout>
    );
  }

  // --- Login view (default) ---
  return (
    <div className="auth-page auth-page--split">
      <main className="auth-shell" aria-label="Sign in">
        <section className="auth-panel auth-panel-left auth-panel-left--login">
          <header className="auth-panel-header">
            <Link to="/" className="auth-logo">
              <span className="auth-logo-icon" aria-hidden>
                <LogoMark size={30} />
              </span>
              <span className="auth-logo-text">Bank Statement Scanner</span>
            </Link>
          </header>

          <div className="auth-card auth-card--form">
            <h1 className="auth-title auth-title-left">Welcome back</h1>
            <p className="auth-description auth-description-left">
              Log in to manage your financial statements.
            </p>

            <form onSubmit={handleLogin} className="auth-form">
              <label className="auth-label">Email address</label>
              <input
                type="email"
                className="auth-input"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@company.com"
                required
                autoComplete="email"
              />
              <div className="auth-label-row">
                <label className="auth-label">Password</label>
                <Link to="/forgot-password" className="auth-link-inline">Forgot password?</Link>
              </div>
              <PasswordInput
                className="auth-input"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
              />
              <label className="auth-checkbox-row">
                <input
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                />
                <span>Remember me for 30 days</span>
              </label>
              <button type="submit" className="auth-btn auth-btn-primary auth-btn-block" disabled={loading}>
                {loading ? "Signing in…" : "Sign in"}
              </button>
            </form>

            <div className="auth-divider">OR CONTINUE WITH</div>
            <div className="auth-social auth-social-row">
              <button
                type="button"
                className="auth-btn auth-btn-provider"
                onClick={() => handleSocialLogin("google")}
                disabled={loading}
              >
                <GoogleLogo className="auth-btn-google-icon" />
                <span>Google</span>
              </button>
            </div>

            {message.text && (
              <p className={`auth-message auth-message-${message.type}`} role="alert">
                {message.text}
              </p>
            )}

            <p className="auth-footer auth-footer-left">
              Don&apos;t have an account?{" "}
              <Link to="/signup">Sign up for free</Link>
            </p>
          </div>

          <footer className="auth-shell-footer auth-shell-footer--login">
            <Link to="/privacy-policy" className="auth-footer-link">Privacy Policy</Link>
            <Link to="/terms-of-service" className="auth-footer-link">Terms of Service</Link>
            <a href="/security" className="auth-footer-link">Security</a>
            <Link to="/contact" className="auth-footer-link">Contact Support</Link>
          </footer>
        </section>

        <section className="auth-panel auth-panel-right auth-panel-right--login" aria-label="Why Bank Statement Scanner">
          <div className="auth-right-inner">
            <h2 className="auth-right-title">Your statements are where you left them.</h2>
            <ul className="auth-right-list" role="list">
              <li>Every statement you&rsquo;ve converted, ready to open</li>
              <li>Ask any of them for the rows you need</li>
              <li>Download Excel or CSV again, for QuickBooks, Xero or your workbook</li>
            </ul>
            <p className="auth-right-note">No bank login needed. We only read the PDFs you upload.</p>
          </div>
        </section>
      </main>
    </div>
  );
}
