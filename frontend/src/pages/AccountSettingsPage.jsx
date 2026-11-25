import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import AppLayout from "../components/AppLayout";
import { useAuth } from "../contexts/AuthContext";
import { useUsage } from "../contexts/UsageContext";
import { supabase } from "../lib/supabase";
import { createCheckoutSession, deleteAccount, getBillingBalance } from "../api/client";
import { OFFERS, getOffer } from "../lib/offer";
import { describeDiscount, discountedPrice, formatPrice } from "../lib/referral";
import { ACCURATE_MULTIPLIER, BULK_PACK, FREE_SIGNUP_PAGES, PAGE_PACKS, PLAN_PAGES, PLAN_PRICE, formatExpiry } from "../lib/pricing";
import "./AccountSettingsPage.css";
import "./AuthPage.css";
import PasswordInput from "../components/PasswordInput";

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
        if (!cancelled) setBillingBalance({ pages_remaining: 0, free_pages: 0, plan_pages: 0, pack_pages: 0, subscription_active: false });
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
  // "Get more pages" links here as /settings#billing: scroll once the section renders.
  useEffect(() => {
    if (billingBalance && window.location.hash === "#billing") {
      document.getElementById("billing")?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [billingBalance]);
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

  const offer = getOffer(user);
  // Show the balance the sidebar already loaded right away; /api/billing/balance
  // (which adds the referral discount) replaces it when it arrives.
  const { usage } = useUsage();
  const balance = billingBalance ?? (usage?.authenticated && usage.pages_remaining != null ? usage : null);
  // Affiliate referral discount (server-side terms; checkout applies it).
  const referral = billingBalance?.referral_discount ?? null;
  const planDiscount = referral?.plan_eligible ? referral : null;
  const planPriceLabel = planDiscount
    ? `${formatPrice(discountedPrice(PLAN_PRICE, planDiscount.pct))}/month${planDiscount.months ? ` for ${planDiscount.months} month${planDiscount.months === 1 ? "" : "s"}` : ""}`
    : `$${PLAN_PRICE}/month`;
  const packPrice = (price) => (referral?.packs ? discountedPrice(price, referral.pct) : price);

  const handleSubscribe = async () => {
    setBillingLoading(true);
    setBillingMessage({ type: "", text: "" });
    try {
      const url = await createCheckoutSession("subscription", user?.email ?? undefined, offer);
      if (url) window.location.href = url;
    } catch (err) {
      setError(setBillingMessage, err.message || "Failed to start checkout");
    } finally {
      setBillingLoading(false);
    }
  };

  const handleBuyPack = async (packId) => {
    setBillingLoading(true);
    setBillingMessage({ type: "", text: "" });
    try {
      const url = await createCheckoutSession("topup", user?.email ?? undefined, null, undefined, packId);
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
      <div className="account-settings" data-clarity-mask="true">
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
            <PasswordInput
              id="settings-password"
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
            <PasswordInput
              id="settings-confirm-password"
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

        <section className="account-settings-section" id="billing">
          <h2 className="account-settings-section-title">Billing</h2>
          <p className="account-settings-description">
            You pay per PDF page. Your first month includes {FREE_SIGNUP_PAGES} free pages.
          </p>
          {balance === null && <div className="account-settings-billing-skeleton" aria-hidden="true" />}
          {balance !== null && (
            <>
              <p className="account-settings-billing-balance">
                <strong>{(balance.pages_remaining ?? 0).toLocaleString()}</strong> pages left
              </p>
              <ul className="account-settings-billing-breakdown">
                {balance.free_pages > 0 && (
                  <li>
                    {balance.free_pages} free pages
                    {formatExpiry(balance.free_expires_at) ? `, valid until ${formatExpiry(balance.free_expires_at)}` : ""}
                  </li>
                )}
                {balance.subscription_active && <li>{balance.plan_pages ?? 0} of {PLAN_PAGES} plan pages left this month</li>}
                {balance.pack_pages > 0 && <li>{balance.pack_pages} page-pack pages (never expire)</li>}
                {balance.frozen_pages > 0 && (
                  <li>{balance.frozen_pages} subscriber pack pages paused. Subscribe again to use them.</li>
                )}
              </ul>
              {referral && (planDiscount || referral.packs) && (
                <p className="account-settings-offer">
                  Referral code {referral.code.toUpperCase()}: {planDiscount ? describeDiscount(referral) : `${referral.pct}% off page packs`}
                  {referral.packs && formatExpiry(referral.packs_ends_at) ? ` (packs until ${formatExpiry(referral.packs_ends_at)})` : ""}.
                </p>
              )}
              {balance.subscription_active ? (
                <>
                  <h3 className="account-settings-subtitle">Page packs</h3>
                  <p className="account-settings-description">
                    One-time add-on for subscribers. Pack pages never expire and are used after your plan pages. If you cancel, they pause until you subscribe again. High accuracy mode uses {ACCURATE_MULTIPLIER} pages per PDF page.
                  </p>
                  <div className="account-settings-packs">
                    {PAGE_PACKS.map((p) => (
                      <button
                        key={p.id}
                        type="button"
                        className="account-settings-pack"
                        onClick={() => handleBuyPack(p.id)}
                        disabled={billingLoading}
                      >
                        <span className="account-settings-pack-pages">{p.pages} pages</span>
                        <span className="account-settings-pack-price">
                          {packPrice(p.price) !== p.price && <s className="account-settings-pack-was">${p.price}</s>}{" "}
                          {formatPrice(packPrice(p.price))}
                        </span>
                      </button>
                    ))}
                  </div>
                </>
              ) : (
                <>
                  <h3 className="account-settings-subtitle">Choose how to get more pages</h3>
                  <div className="billing-plans">
                    <article className="billing-plan billing-plan--recommended" aria-labelledby="plan-monthly">
                      <span className="billing-plan-badge">Recommended · best value</span>
                      <h4 className="billing-plan-name" id="plan-monthly">Monthly plan</h4>
                      <p className="billing-plan-price">
                        {planDiscount ? (
                          <>
                            <s className="account-settings-pack-was">${PLAN_PRICE}</s>{" "}
                            {formatPrice(discountedPrice(PLAN_PRICE, planDiscount.pct))}
                          </>
                        ) : (
                          `$${PLAN_PRICE}`
                        )}
                        <span>/month</span>
                      </p>
                      <p className="billing-plan-rate">
                        {PLAN_PAGES} pages a month · about {Math.round((PLAN_PRICE / PLAN_PAGES) * 100)}¢ a page
                      </p>
                      <ul className="billing-plan-list" role="list">
                        <li>{PLAN_PAGES} pages every billing cycle</li>
                        <li>Add page packs from ${PAGE_PACKS[0].price} in busy months</li>
                        <li>Larger uploads, up to 50 MB</li>
                        <li>Cancel anytime</li>
                      </ul>
                      {offer && <p className="billing-plan-note">{OFFERS[offer].label}.</p>}
                      <button
                        type="button"
                        className="billing-plan-cta billing-plan-cta--primary"
                        onClick={handleSubscribe}
                        disabled={billingLoading}
                      >
                        {billingLoading ? "Redirecting…" : offer ? OFFERS[offer].cta : `Subscribe for ${planPriceLabel}`}
                      </button>
                    </article>
                    <article className="billing-plan" aria-labelledby="plan-once">
                      <h4 className="billing-plan-name" id="plan-once">Pay once</h4>
                      <p className="billing-plan-price">
                        {packPrice(BULK_PACK.price) !== BULK_PACK.price && <s className="account-settings-pack-was">${BULK_PACK.price}</s>}{" "}
                        {formatPrice(packPrice(BULK_PACK.price))}
                      </p>
                      <p className="billing-plan-rate">
                        {BULK_PACK.pages} pages · about {Math.round((packPrice(BULK_PACK.price) / BULK_PACK.pages) * 100)}¢ a page
                      </p>
                      <ul className="billing-plan-list" role="list">
                        <li>{BULK_PACK.pages} pages, one payment</li>
                        <li>Pages never expire</li>
                        <li>No subscription</li>
                      </ul>
                      <button
                        type="button"
                        className="billing-plan-cta"
                        onClick={() => handleBuyPack(BULK_PACK.id)}
                        disabled={billingLoading}
                      >
                        {billingLoading ? "Redirecting…" : `Buy ${BULK_PACK.pages} pages`}
                      </button>
                    </article>
                  </div>
                  <p className="billing-plans-fine">
                    Payments are handled securely by Stripe. High accuracy mode uses {ACCURATE_MULTIPLIER} pages per PDF page.
                  </p>
                </>
              )}
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
