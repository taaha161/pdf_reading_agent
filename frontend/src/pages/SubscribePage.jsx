import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { createCheckoutSession, getBillingBalance, startPaidSignup } from "../api/client";
import { getPendingReferral } from "../lib/referral";
import { getOffer } from "../lib/offer";
import SignupLayout, { BenefitList, SecurityList, SocialProof, ValuePanel } from "../components/SignupLayout";
import { PLAN_PAGES, PLAN_PRICE } from "../lib/pricing";

/**
 * /subscribe: the pricing page's "Get Monthly" button.
 * Signed out: guest Stripe Checkout (pay first; the account is created after payment).
 * Signed in: the normal subscription checkout for that account (or Account if already subscribed).
 */
export default function SubscribePage() {
  const { user, accessToken, loading: authLoading } = useAuth();
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  const started = useRef(-1);

  useEffect(() => {
    if (authLoading || started.current === attempt) return;
    started.current = attempt;
    setError("");
    (async () => {
      try {
        let url;
        if (user && accessToken) {
          const balance = await getBillingBalance(accessToken).catch(() => null);
          if (balance?.subscription_active) {
            window.location.replace("/settings");
            return;
          }
          url = await createCheckoutSession("subscription", user.email ?? undefined, getOffer(user), accessToken);
        } else {
          url = await startPaidSignup(getPendingReferral());
        }
        if (!url) throw new Error("Couldn't start checkout. Please try again.");
        window.location.assign(url);
      } catch (e) {
        setError(e.message || "Couldn't start checkout. Please try again.");
      }
    })();
  }, [user, accessToken, authLoading, attempt]);

  return (
    <SignupLayout
      aside={
        <ValuePanel eyebrow="Monthly plan" title={`$${PLAN_PRICE}/month for ${PLAN_PAGES} pages`} lead="Cancel anytime. No annual contract.">
          <BenefitList items={[`${PLAN_PAGES} statement pages every month`, "CSV & Excel export, AI categorization", "Ask your statements questions"]} />
          <SecurityList />
          <SocialProof />
        </ValuePanel>
      }
    >
      {error ? (
        <div className="su-state" role="alert">
          <span className="su-state-icon su-state-icon--warn" aria-hidden>!</span>
          <h2 className="su-title">Checkout didn&apos;t open</h2>
          <p className="su-sub">{error}</p>
          <div className="su-state-actions">
            <button type="button" className="su-btn su-btn-primary" onClick={() => setAttempt((a) => a + 1)}>Try again</button>
            <Link to="/" className="su-btn su-btn-secondary">Back to pricing</Link>
          </div>
        </div>
      ) : (
        <div className="su-state" role="status" aria-live="polite">
          <span className="su-state-icon"><span className="su-spinner" /></span>
          <h2 className="su-title">Taking you to secure checkout…</h2>
          <p className="su-sub">Payment is handled by Stripe. You&apos;ll set up your login right after paying.</p>
        </div>
      )}
    </SignupLayout>
  );
}
