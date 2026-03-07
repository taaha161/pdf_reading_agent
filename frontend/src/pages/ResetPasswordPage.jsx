import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { supabase } from "../lib/supabase";
import { useAuth } from "../contexts/AuthContext";
import "./AuthPage.css";

export default function ResetPasswordPage() {
  const navigate = useNavigate();
  const { user, loading: authLoading } = useAuth();
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState({ type: "", text: "" });
  const [done, setDone] = useState(false);

  // Supabase puts tokens in hash on redirect; session is set after client parses it
  const [hasRecoverySession, setHasRecoverySession] = useState(() => {
    const hash = window.location.hash;
    const params = new URLSearchParams(hash.replace("#", ""));
    return params.get("type") === "recovery";
  });

  useEffect(() => {
    if (user && window.location.hash) {
      setHasRecoverySession(true);
      window.history.replaceState(null, "", window.location.pathname);
    }
  }, [user]);

  const setError = (text) => setMessage({ type: "error", text });
  const setSuccess = (text) => setMessage({ type: "success", text });

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }
    if (password.length < 6) {
      setError("Password must be at least 6 characters");
      return;
    }
    setLoading(true);
    setMessage({ type: "", text: "" });
    try {
      const { error } = await supabase.auth.updateUser({ password });
      if (error) throw error;
      setDone(true);
      setSuccess("Your password has been updated. You can now log in.");
      setTimeout(() => navigate("/login", { replace: true }), 2000);
    } catch (err) {
      setError(err.message || "Failed to update password");
    } finally {
      setLoading(false);
    }
  };

  if (authLoading && !user) {
    return (
      <div className="auth-page">
        <div className="auth-card">
          <p className="auth-description">Loading…</p>
        </div>
      </div>
    );
  }

  const showForm = hasRecoverySession || user;
  if (!showForm) {
    return (
      <div className="auth-page">
        <div className="auth-card">
          <h1 className="auth-title">Reset password</h1>
          <p className="auth-message auth-message-error">
            This page is for setting a new password. Use the link we sent to your email, or request a new one.
          </p>
          <Link to="/forgot-password" className="auth-btn auth-btn-primary" style={{ display: "block", textAlign: "center", textDecoration: "none" }}>
            Send reset link
          </Link>
          <Link to="/login" className="auth-back">← Back to log in</Link>
        </div>
      </div>
    );
  }

  if (done) {
    return (
      <div className="auth-page">
        <div className="auth-card">
          <h1 className="auth-title">Password updated</h1>
          <p className="auth-message auth-message-success">{message.text}</p>
          <Link to="/login" className="auth-link-inline">Go to log in</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <h1 className="auth-title">Set new password</h1>
        <p className="auth-description">
          Enter your new password below.
        </p>
        <form onSubmit={handleSubmit} className="auth-form">
          <label className="auth-label">New password</label>
          <input
            type="password"
            className="auth-input"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="At least 6 characters"
            required
            minLength={6}
            autoComplete="new-password"
          />
          <label className="auth-label">Confirm new password</label>
          <input
            type="password"
            className="auth-input"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            placeholder="Repeat your password"
            required
            minLength={6}
            autoComplete="new-password"
          />
          <button type="submit" className="auth-btn auth-btn-primary" disabled={loading}>
            {loading ? "Updating…" : "Update password"}
          </button>
        </form>
        {message.text && (
          <p className={`auth-message auth-message-${message.type}`} role="alert">
            {message.text}
          </p>
        )}
        <Link to="/login" className="auth-back">← Back to log in</Link>
      </div>
    </div>
  );
}
