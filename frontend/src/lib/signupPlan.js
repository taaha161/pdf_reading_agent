// Plan picked on the signup form: "subscription" (default) or "trial" (free scans only).
//
// Email signups store it in Supabase user_metadata, so it survives the user
// confirming their email in another browser. OAuth signups can't attach
// metadata before the account exists, so the choice is also kept in
// localStorage and applied on the first sign-in of a just-created account.
// Once checkout starts, `signup_checkout_started` is set on the account so
// cancelling Stripe checkout doesn't bounce the user back to it forever.
import { supabase } from "./supabase";

export const PLAN_SUBSCRIPTION = "subscription";
export const PLAN_TRIAL = "trial";

const PENDING_KEY = "bss_signup_plan";
const PENDING_TTL_MS = 7 * 24 * 60 * 60 * 1000;
const NEW_ACCOUNT_MS = 10 * 60 * 1000;

export function rememberSignupPlan(plan) {
  try {
    localStorage.setItem(PENDING_KEY, JSON.stringify({ plan, at: Date.now() }));
  } catch {
    /* storage blocked: email signups still carry it in metadata */
  }
}

function readPendingPlan() {
  try {
    const pending = JSON.parse(localStorage.getItem(PENDING_KEY) || "null");
    if (!pending || !(Date.now() - pending.at < PENDING_TTL_MS)) return null;
    return pending.plan;
  } catch {
    return null;
  }
}

function clearPendingPlan() {
  try {
    localStorage.removeItem(PENDING_KEY);
  } catch {
    /* ignore */
  }
}

/** True if this account chose the subscription at signup and hasn't been sent to checkout yet. */
export function needsSignupCheckout(user) {
  if (!user?.id) return false;
  const meta = user.user_metadata ?? {};
  if (meta.signup_checkout_started) return false;
  if (meta.signup_plan) return meta.signup_plan === PLAN_SUBSCRIPTION;
  // OAuth signup: only a just-created account picks up the stored choice.
  const age = Date.now() - Date.parse(user.created_at ?? "");
  if (!(age >= 0 && age < NEW_ACCOUNT_MS)) return false;
  return readPendingPlan() === PLAN_SUBSCRIPTION;
}

/** Record that checkout was started so it only happens once per account. */
export async function markSignupCheckoutStarted() {
  clearPendingPlan();
  try {
    await supabase.auth.updateUser({ data: { signup_checkout_started: true } });
  } catch {
    /* best-effort */
  }
}
