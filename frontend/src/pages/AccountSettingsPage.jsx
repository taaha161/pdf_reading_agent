import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import AppLayout from "../components/AppLayout";
import { useAuth } from "../contexts/AuthContext";
import { supabase } from "../lib/supabase";
import { createCheckoutSession, deleteAccount, getBillingBalance } from "../api/client";
import "./AccountSettingsPage.css";
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

export default function AccountSettingsPage() {
  const navigate = useNavigate();
  const { user, signOut } = useAuth();
  const currentName = (user?.user_metadata?.full_name ?? "").trim() || "";

  const [name, setName] = useState(currentName);
  useEffect(() => {
    setName(currentName);
  }, [currentName]);

  useEffect(() => {
    if (!user) return;
    let cancelled = false;
    (async () => {
      try {
        const data = await getBillingBalance();
        if (!cancelled) setBillingBalance(data);
      } catch {
        if (!cancelled) setBillingBalance({ balance_cents: 0, subscription_active: false });
      }
    })();
    return () => { cancelled = true; };
  }, [user]);
  const [nameLoading, setNameLoading] = useState(false);
  const [nameMessage, setNameMessage] = useState({ type: "", text: "" });

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordLoading, setPasswordLoading] = useState(false);
  const [passwordMessage, setPasswordMessage] = useState({ type: "", text: "" });

  const [deleteConfirm, setDeleteConfirm] = useState("");
  const [deleteChecked, setDeleteChecked] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [deleteMessage, setDeleteMessage] = useState({ type: "", text: "" });

  const [billingBalance, setBillingBalance] = useState(null);
  const [billingLoading, setBillingLoading] = useState(false);
  const [billingMessage, setBillingMessage] = useState({ type: "", text: "" });

  const setError = (setter, text) => setter({ type: "error", text });
  const setSuccess = (setter, text) => setter({ type: "success", text });

  const handleNameSubmit = async (e) => {
    e.preventDefault();
    const trimmed = name.trim();
    if (trimmed === currentName) {
      setNameMessage({ type: "", text: "" });
      return;
    }
    setNameLoading(true);
    setNameMessage({ type: "", text: "" });
    try {
      const { error } = await supabase.auth.updateUser({ data: { full_name: trimmed } });
      if (error) throw error;
      setSuccess(setNameMessage, "Name updated.");
    } catch (err) {
      setError(setNameMessage, err.message || "Failed to update name");
    } finally {
      setNameLoading(false);
    }
  };

  const handlePasswordSubmit = async (e) => {
    e.preventDefault();
    if (password !== confirmPassword) {
      setError(setPasswordMessage, "Passwords do not match");
      return;
    }
    const strength = validatePasswordStrength(password);
    if (!strength.ok) {
      setError(setPasswordMessage, `Password must have: ${strength.message}`);
      return;
    }
    setPasswordLoading(true);
    setPasswordMessage({ type: "", text: "" });
    try {
      const { error } = await supabase.auth.updateUser({ password });
      if (error) throw error;
      setSuccess(setPasswordMessage, "Password updated.");
      setPassword("");
      setConfirmPassword("");
    } catch (err) {
      setError(setPasswordMessage, err.message || "Failed to update password");
    } finally {
      setPasswordLoading(false);
    }
  };

  const handleSubscribe = async () => {
    setBillingLoading(true);
    setBillingMessage({ type: "", text: "" });
    try {
      const url = await createCheckoutSession("subscription", user?.email ?? undefined);
      if (url) window.location.href = url;
    } catch (err) {
      setError(setBillingMessage, err.message || "Failed to start checkout");
    } finally {
      setBillingLoading(false);
    }
  };

  const handleAddCredits = async () => {
    setBillingLoading(true);
    setBillingMessage({ type: "", text: "" });
    try {
      const url = await createCheckoutSession("topup", user?.email ?? undefined);
      if (url) window.location.href = url;
    } catch (err) {
      setError(setBillingMessage, err.message || "Failed to start checkout");
    } finally {
      setBillingLoading(false);
    }
  };

  const handleDeleteSubmit = async (e) => {
    e.preventDefault();
    if (!deleteChecked || deleteConfirm.trim().toUpperCase() !== "DELETE") {
      setError(setDeleteMessage, "Please confirm by checking the box and typing DELETE.");
      return;
    }
    setDeleteLoading(true);
    setDeleteMessage({ type: "", text: "" });
    try {
      await deleteAccount();
      signOut();
      navigate("/", { replace: true });
    } catch (err) {
      setError(setDeleteMessage, err.message || "Failed to delete account");
    } finally {
      setDeleteLoading(false);
    }
  };

  return (
    <AppLayout>
      <div className="account-settings">
        <header className="account-settings-head">
          <h1 className="account-settings-title">Account settings</h1>
          <p className="account-settings-description">
            Manage your profile, password, and account.
          </p>
        </header>

        <section className="account-settings-section">
          <h2 className="account-settings-section-title">Display name</h2>
          <form onSubmit={handleNameSubmit} className="auth-form">
            <label className="auth-label" htmlFor="settings-name">Name</label>
            <input
              id="settings-name"
              type="text"
              className="auth-input"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Your name"
              autoComplete="name"
            />
            <button type="submit" className="auth-btn auth-btn-primary" disabled={nameLoading}>
              {nameLoading ? "Saving…" : "Save name"}
            </button>
          </form>
          {nameMessage.text && (
            <p className={`auth-message auth-message-${nameMessage.type}`} role="alert">
              {nameMessage.text}
            </p>
          )}
        </section>

        <section className="account-settings-section">
          <h2 className="account-settings-section-title">Reset password</h2>
          <form onSubmit={handlePasswordSubmit} className="auth-form">
            <label className="auth-label" htmlFor="settings-password">New password</label>
            <input
              id="settings-password"
              type="password"
              className="auth-input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="At least 8 characters, upper, lower, number, special"
              minLength={PASSWORD_MIN_LENGTH}
              autoComplete="new-password"
            />
            <p className="auth-password-hint">
              Use at least 8 characters including one uppercase letter, one lowercase letter, one number, and one special character (!@#$%^&* etc.).
            </p>
            <label className="auth-label" htmlFor="settings-confirm-password">Confirm new password</label>
            <input
              id="settings-confirm-password"
              type="password"
              className="auth-input"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Repeat your password"
              minLength={PASSWORD_MIN_LENGTH}
              autoComplete="new-password"
            />
            <button type="submit" className="auth-btn auth-btn-primary" disabled={passwordLoading}>
              {passwordLoading ? "Updating…" : "Update password"}
            </button>
          </form>
          {passwordMessage.text && (
            <p className={`auth-message auth-message-${passwordMessage.type}`} role="alert">
              {passwordMessage.text}
            </p>
          )}
        </section>

        <section className="account-settings-section">
          <h2 className="account-settings-section-title">Billing</h2>
          <p className="account-settings-description">
            Credits are used for scans. Light (fast) = $0.005, Normal (balanced) = $1, High accuracy = $1.50. $10/month gives you $10 in credits; add more when you run out.
          </p>
          {billingBalance !== null && (
            <>
              <p className="account-settings-billing-balance">
                <strong>{(billingBalance.balance_cents / 100).toFixed(2)}</strong> credits remaining
              </p>
              <div className="account-settings-billing-actions">
                {!billingBalance.subscription_active ? (
                  <button
                    type="button"
                    className="auth-btn auth-btn-primary"
                    onClick={handleSubscribe}
                    disabled={billingLoading}
                  >
                    {billingLoading ? "Redirecting…" : "Subscribe — $10/month"}
                  </button>
                ) : (
                  <button
                    type="button"
                    className="auth-btn auth-btn-primary"
                    onClick={handleAddCredits}
                    disabled={billingLoading}
                  >
                    {billingLoading ? "Redirecting…" : "Add credits"}
                  </button>
                )}
              </div>
            </>
          )}
          {billingMessage.text && (
            <p className={`auth-message auth-message-${billingMessage.type}`} role="alert">
              {billingMessage.text}
            </p>
          )}
        </section>

        <section className="account-settings-section account-settings-danger">
          <h2 className="account-settings-section-title">Delete account</h2>
          <p className="account-settings-danger-text">
            Permanently delete your account and all associated data. This cannot be undone.
          </p>
          <form onSubmit={handleDeleteSubmit} className="auth-form">
            <label className="account-settings-checkbox-label">
              <input
                type="checkbox"
                checked={deleteChecked}
                onChange={(e) => setDeleteChecked(e.target.checked)}
                className="account-settings-checkbox"
              />
              I understand this will permanently delete my account and all data.
            </label>
            <label className="auth-label" htmlFor="settings-delete-confirm">
              Type <strong>DELETE</strong> to confirm
            </label>
            <input
              id="settings-delete-confirm"
              type="text"
              className="auth-input"
              value={deleteConfirm}
              onChange={(e) => setDeleteConfirm(e.target.value)}
              placeholder="DELETE"
              autoComplete="off"
            />
            <button
              type="submit"
              className="auth-btn account-settings-delete-btn"
              disabled={deleteLoading || !deleteChecked || deleteConfirm.trim().toUpperCase() !== "DELETE"}
            >
              {deleteLoading ? "Deleting…" : "Delete my account"}
            </button>
          </form>
          {deleteMessage.text && (
            <p className={`auth-message auth-message-${deleteMessage.type}`} role="alert">
              {deleteMessage.text}
            </p>
          )}
        </section>
      </div>
    </AppLayout>
  );
}
