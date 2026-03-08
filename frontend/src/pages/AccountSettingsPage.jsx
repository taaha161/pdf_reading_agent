import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import AppLayout from "../components/AppLayout";
import { useAuth } from "../contexts/AuthContext";
import { supabase } from "../lib/supabase";
import { deleteAccount } from "../api/client";
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
