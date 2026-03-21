import { useState, useEffect } from "react";
import { Link, useNavigate, useLocation, useSearchParams } from "react-router-dom";
import { supabase } from "../lib/supabase";
import { sendTikTokSignupEvent } from "../lib/tiktokSignupEvent";
import { useAuth } from "../contexts/AuthContext";
import logo from "../assets/pdf_to_excel_logo.png";
import "./AuthPage.css";

const PASSWORD_MIN_LENGTH = 8;

/** Google G logo SVG (official brand colors) */
function GoogleLogo({ className }) {
  return (
    <svg className={className} width="20" height="20" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" aria-hidden>
      <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
      <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
      <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
      <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
    </svg>
  );
}

/** Shield icon for \"Smart Categorization\" card */
function ShieldIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden focusable="false">
      <path
        d="M12 3 6 5v6c0 4.1 2.7 7.5 6 8.5 3.3-1 6-4.4 6-8.5V5l-6-2Z"
        fill="currentColor"
      />
      <path
        d="M10.5 12.5 12 14l3-3"
        fill="none"
        stroke="#0f172a"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/** Lightning bolt icon for \"Instant Processing\" */
function BoltIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden focusable="false">
      <path
        d="M13 2 5 13h5l-1 9 8-11h-5l1-9Z"
        fill="currentColor"
      />
    </svg>
  );
}

/** Strong password: min 8 chars, uppercase, lowercase, number, special char */
function validatePasswordStrength(password) {
  if (!password || password.length < PASSWORD_MIN_LENGTH) return { ok: false, message: `At least ${PASSWORD_MIN_LENGTH} characters` };
  if (!/[A-Z]/.test(password)) return { ok: false, message: "One uppercase letter" };
  if (!/[a-z]/.test(password)) return { ok: false, message: "One lowercase letter" };
  if (!/[0-9]/.test(password)) return { ok: false, message: "One number" };
  if (!/[^A-Za-z0-9]/.test(password)) return { ok: false, message: "One special character (!@#$%^&* etc.)" };
  return { ok: true };
}

export default function AuthPage({ mode: initialMode = "login" }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuth();
  const [searchParams] = useSearchParams();
  const from = location.state?.from?.pathname || "/dashboard";
  const modeFromQuery = searchParams.get("mode"); // e.g. /login?mode=signup
  const mode = modeFromQuery === "signup" || modeFromQuery === "login" || modeFromQuery === "forgot" ? modeFromQuery : initialMode;

  const [view, setView] = useState(mode); // "login" | "signup" | "forgot-password"
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState({ type: "", text: "" });
  const [signupSuccess, setSignupSuccess] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);

  useEffect(() => {
    setView(mode);
    setMessage({ type: "", text: "" });
    setSignupSuccess(false);
    setConfirmPassword("");
  }, [mode]);

  // Redirect if already logged in (skip on reset-password; that page handles its own logic)
  useEffect(() => {
    if (user && view !== "reset-password") {
      navigate("/dashboard", { replace: true });
    }
  }, [user, view, navigate]);

  const setError = (text) => setMessage({ type: "error", text });
  const setSuccess = (text) => setMessage({ type: "success", text });
  const clearMessage = () => setMessage({ type: "", text: "" });

  const handleSocialLogin = async (provider) => {
    setLoading(true);
    clearMessage();
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

  const handleSignUp = async (e) => {
    e.preventDefault();
    clearMessage();
    const nameTrimmed = fullName.trim();
    if (!nameTrimmed) {
      setError("Name is required so we can recognize you.");
      return;
    }
    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }
    const strength = validatePasswordStrength(password);
    if (!strength.ok) {
      setError(`Password must have: ${strength.message}`);
      return;
    }
    setLoading(true);
    try {
      const { error } = await supabase.auth.signUp({
        email: email.trim(),
        password,
        options: {
          data: { full_name: nameTrimmed },
        },
      });
      if (error) throw error;
      sendTikTokSignupEvent({ email: email.trim() });
      setSignupSuccess(true);
      setSuccess("Check your email to confirm your account. Then you can log in.");
    } catch (err) {
      setError(err.message || "Sign up failed");
    } finally {
      setLoading(false);
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

  // --- Sign up view ---
  if (view === "signup") {
    return (
      <div className="auth-page auth-page--split">
        <header className="auth-header">
          <Link to="/" className="auth-logo">
            <span className="auth-logo-icon" aria-hidden>
              <img src={logo} alt="" />
            </span>
            <span className="auth-logo-text">Bank Statement Scanner</span>
          </Link>
          <div className="auth-header-right">
            <span className="auth-header-copy">Already have an account?</span>
            <Link to="/login" className="auth-header-link">Log In</Link>
          </div>
        </header>

        <main className="auth-shell auth-shell--signup" aria-label="Create account">
          <section className="auth-panel auth-panel-left">
            <h1 className="auth-hero-title">
              Smart financial <span>management starts here.</span>
            </h1>
            <p className="auth-hero-body">
              Join thousands of users who trust Bank Statement Scanner for secure, automated financial insights
              and statement processing.
            </p>
            <div className="auth-feature-stack">
              <div className="auth-feature-card">
                <div className="auth-feature-icon auth-feature-icon--shield" aria-hidden>
                  <ShieldIcon />
                </div>
                <div>
                  <h2>Smart Categorization</h2>
                  <p>Automatically categorize your transactions with AI.</p>
                </div>
              </div>
              <div className="auth-feature-card">
                <div className="auth-feature-icon auth-feature-icon--bolt" aria-hidden>
                  <BoltIcon />
                </div>
                <div>
                  <h2>Convert PDF to Excel in seconds</h2>
                  <p>Scan and convert PDF to Excel in seconds.</p>
                </div>
              </div>
            </div>
            <div className="auth-photo-card" aria-hidden />
            <footer className="auth-shell-footer">
              <button type="button" className="auth-footer-link">Help Center</button>
              <button type="button" className="auth-footer-link">Security</button>
              <button type="button" className="auth-footer-link">Contact Sales</button>
            </footer>
          </section>

          <section className="auth-panel auth-panel-right">
            <div className="auth-card auth-card--elevated">
              <h2 className="auth-title">Create your account</h2>
              <p className="auth-description">
                Start managing your finances securely today.
              </p>

              {signupSuccess ? (
                <div className="auth-success-block">
                  <p className="auth-message auth-message-success">
                    We sent a confirmation link to <strong>{email}</strong>. Click the link in that email to activate your
                    account, then log in below.
                  </p>
                  <Link
                    to="/login"
                    className="auth-btn auth-btn-primary"
                    style={{ textDecoration: "none", textAlign: "center" }}
                  >
                    Go to log in
                  </Link>
                </div>
              ) : (
                <>
                  <form onSubmit={handleSignUp} className="auth-form">
                    <label className="auth-label">Full Name</label>
                    <input
                      type="text"
                      className="auth-input"
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      placeholder="John Doe"
                      required
                      minLength={1}
                      autoComplete="name"
                    />
                    <label className="auth-label">Email Address</label>
                    <input
                      type="email"
                      className="auth-input"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="email@example.com"
                      required
                      autoComplete="email"
                    />
                    <label className="auth-label">Password</label>
                    <input
                      type="password"
                      className="auth-input"
                      name="password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="Min. 8 characters"
                      required
                      minLength={PASSWORD_MIN_LENGTH}
                      autoComplete="new-password"
                    />
                    <label className="auth-label">Confirm password</label>
                    <input
                      type="password"
                      className="auth-input"
                      name="confirm-password"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      placeholder="Re-enter your password"
                      required
                      minLength={PASSWORD_MIN_LENGTH}
                      autoComplete="new-password"
                    />
                    <label className="auth-checkbox-row">
                      <input type="checkbox" required />
                      <span>
                        I agree to the{" "}
                        <Link to="/terms-of-service" className="auth-link-inline">Terms of Service</Link>{" "}
                        and{" "}
                        <Link to="/privacy-policy" className="auth-link-inline">Privacy Policy</Link>.
                      </span>
                    </label>
                    <button type="submit" className="auth-btn auth-btn-primary auth-btn-block" disabled={loading}>
                      {loading ? "Creating account…" : "Create Account →"}
                    </button>
                  </form>

                  <div className="auth-divider">OR SIGN UP WITH</div>
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
                    {/* <button
                      type="button"
                      className="auth-btn auth-btn-provider"
                      onClick={() => handleSocialLogin("github")}
                      disabled={loading}
                    >
                      <span className="auth-provider-icon">G</span>
                      <span>GitHub</span>
                    </button> */}
                  </div>
                </>
              )}

              {!signupSuccess && message.text && (
                <p className={`auth-message auth-message-${message.type}`} role="alert">
                  {message.text}
                </p>
              )}
            </div>

            <p className="auth-shell-copy">
              © {new Date().getFullYear()} Bank Statement Scanner Inc. All rights reserved. Your data is handled according to our
              standard security protocols.
            </p>
          </section>
        </main>
      </div>
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
                <img src={logo} alt="" />
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
              <input
                type="password"
                className="auth-input"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
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
              {/*
              <button
                type="button"
                className="auth-btn auth-btn-provider"
                onClick={() => handleSocialLogin("apple")}
                disabled={loading}
              >
                <span className="auth-provider-icon"></span>
                <span>Apple</span>
              </button>
              */}
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
            <button type="button" className="auth-footer-link">Security</button>
            <button type="button" className="auth-footer-link">Contact Support</button>
          </footer>
        </section>

        <section className="auth-panel auth-panel-right auth-panel-right--login" aria-label="Why Bank Statement Scanner">
          <div className="auth-right-inner">
            {/* Add your SVG to public/auth-illustration.svg to replace the placeholder */}
            <div className="auth-illustration-icon" aria-hidden>
              <img src="/auth-illustration.svg" alt="" className="auth-illustration-icon-img" />
            </div>
            <h2 className="auth-right-title">Automate your financial data entry today.</h2>
            <p className="auth-right-body">
              Connect your statements, scan and categorize transactions with AI, and sync everything to your favorite
              accounting software in seconds.
            </p>
            <div className="auth-trust-row">
              <div className="auth-avatar-group" aria-hidden>
                {/* Add your images to public/auth-avatars/ as avatar-1.jpg, avatar-2.jpg, avatar-3.jpg */}
                <span className="auth-avatar auth-avatar--img" style={{ backgroundImage: "url(/auth-avatars/avatar-1.jpg)" }} />
                <span className="auth-avatar auth-avatar--img" style={{ backgroundImage: "url(/auth-avatars/avatar-2.jpg)" }} />
                <span className="auth-avatar auth-avatar--img" style={{ backgroundImage: "url(/auth-avatars/avatar-3.jpg)" }} />
                <span className="auth-badge">10k+</span>
              </div>
              <div className="auth-trust-copy">
                <span className="auth-trust-label">Trusted by 10,000+ finance professionals</span>
              </div>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
