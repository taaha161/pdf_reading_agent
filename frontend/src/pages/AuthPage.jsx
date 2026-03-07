import { useState, useEffect } from "react";
import { Link, useNavigate, useLocation, useSearchParams } from "react-router-dom";
import { supabase } from "../lib/supabase";
import { useAuth } from "../contexts/AuthContext";
import "./AuthPage.css";

const PASSWORD_MIN_LENGTH = 8;

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

  useEffect(() => {
    setView(mode);
    setMessage({ type: "", text: "" });
    setSignupSuccess(false);
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
      <div className="auth-page">
        <div className="auth-card">
          <h1 className="auth-title">Create an account</h1>
          <p className="auth-description">
            Sign up with email or use Google to get started.
          </p>

          <div className="auth-social">
            <button
              type="button"
              className="auth-btn auth-btn-google"
              onClick={() => handleSocialLogin("google")}
              disabled={loading}
            >
              Continue with Google
            </button>
          </div>
          <div className="auth-divider">or</div>

          {signupSuccess ? (
            <div className="auth-success-block">
              <p className="auth-message auth-message-success">
                We sent a confirmation link to <strong>{email}</strong>. Click the link in that email to activate your account, then log in below.
              </p>
              <Link to="/login" className="auth-btn auth-btn-primary" style={{ textDecoration: "none", textAlign: "center" }}>
                Go to log in
              </Link>
            </div>
          ) : (
            <form onSubmit={handleSignUp} className="auth-form">
              <label className="auth-label">Full name <span className="auth-required">(required)</span></label>
              <input
                type="text"
                className="auth-input"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Jane Doe"
                required
                minLength={1}
                autoComplete="name"
              />
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
              <label className="auth-label">Password</label>
              <input
                type="password"
                className="auth-input"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Strong password (see requirements below)"
                required
                minLength={PASSWORD_MIN_LENGTH}
                autoComplete="new-password"
              />
              <p className="auth-password-hint">Use at least 8 characters with uppercase, lowercase, a number, and a special character.</p>
              <label className="auth-label">Confirm password</label>
              <input
                type="password"
                className="auth-input"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Repeat your password"
                required
                minLength={PASSWORD_MIN_LENGTH}
                autoComplete="new-password"
              />
              <button type="submit" className="auth-btn auth-btn-primary" disabled={loading}>
                {loading ? "Creating account…" : "Sign up"}
              </button>
            </form>
          )}

          {!signupSuccess && message.text && (
            <p className={`auth-message auth-message-${message.type}`} role="alert">
              {message.text}
            </p>
          )}
          <p className="auth-footer">
            Already have an account? <Link to="/login">Log in</Link>
          </p>
          <Link to="/" className="auth-back">← Back to home</Link>
        </div>
      </div>
    );
  }

  // --- Login view (default) ---
  return (
    <div className="auth-page">
      <div className="auth-card">
        <h1 className="auth-title">Log in</h1>
        <p className="auth-description">
          Use your email or Google to access your account.
        </p>

        <div className="auth-social">
          <button
            type="button"
            className="auth-btn auth-btn-google"
            onClick={() => handleSocialLogin("google")}
            disabled={loading}
          >
            Continue with Google
          </button>
        </div>
        <div className="auth-divider">or</div>

        <form onSubmit={handleLogin} className="auth-form">
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
          <label className="auth-label">Password</label>
          <input
            type="password"
            className="auth-input"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Your password"
            required
            autoComplete="current-password"
          />
          <div className="auth-forgot-row">
            <Link to="/forgot-password" className="auth-link-inline">Forgot password?</Link>
          </div>
          <button type="submit" className="auth-btn auth-btn-primary" disabled={loading}>
            {loading ? "Signing in…" : "Log in"}
          </button>
        </form>

        {message.text && (
          <p className={`auth-message auth-message-${message.type}`} role="alert">
            {message.text}
          </p>
        )}

        <p className="auth-footer">
          Don&apos;t have an account? <Link to="/signup">Sign up</Link>
        </p>
        <Link to="/" className="auth-back">← Back to home</Link>
      </div>
    </div>
  );
}
