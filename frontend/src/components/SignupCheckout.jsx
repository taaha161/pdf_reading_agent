import { useEffect, useRef, useState } from "react";
import { useAuth } from "../contexts/AuthContext";
import { createCheckoutSession, getBillingBalance } from "../api/client";
import { getOffer } from "../lib/offer";
import { markSignupCheckoutStarted, needsSignupCheckout } from "../lib/signupPlan";

/**
 * After a new account that picked the subscription on the signup form signs in
 * for the first time, send it straight to Stripe subscription checkout.
 * Cancelling checkout leaves the account on the free trial.
 */
export default function SignupCheckout() {
  const { user, accessToken } = useAuth();
  const [redirecting, setRedirecting] = useState(false);
  const startedFor = useRef(null);

  useEffect(() => {
    if (!accessToken || !needsSignupCheckout(user) || startedFor.current === user.id) return;
    startedFor.current = user.id;
    (async () => {
      try {
        // Pass the token explicitly: this effect runs before AppContent's effect
        // hands the new session token to the API client, so relying on the
        // shared getter sends the request unauthenticated (401).
        const balance = await getBillingBalance(accessToken);
        if (balance?.subscription_active) {
          await markSignupCheckoutStarted();
          return;
        }
        setRedirecting(true);
        const url = await createCheckoutSession("subscription", user.email ?? undefined, getOffer(user), accessToken);
        await markSignupCheckoutStarted();
        if (url) window.location.href = url;
        else setRedirecting(false);
      } catch (err) {
        // Billing unavailable: leave them on the free trial; they can subscribe from Account.
        // Not marked as started, so the next sign-in tries again.
        console.error("Signup checkout redirect failed:", err);
        setRedirecting(false);
      }
    })();
  }, [user, accessToken]);

  if (!redirecting) return null;
  return (
    <div className="signup-checkout-overlay" role="status" aria-live="polite">
      <p>Taking you to checkout…</p>
    </div>
  );
}
