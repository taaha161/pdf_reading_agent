// Copy for "this scan needs more pages than you have", shared by the scanner, bulk upload and signup/login.
import { BULK_PACK, FREE_ANON_PAGES, FREE_SIGNUP_PAGES, PLAN_PAGES, PLAN_PRICE } from "./pricing";

const pages = (n) => `${Number(n).toLocaleString()} page${n === 1 ? "" : "s"}`;

/** Router state for /signup and /login when a guest's PDF is bigger than the free pages left. */
export function pagesExceededState({ pages_required = 0, pages_remaining = 0 } = {}) {
  return { reason: "pages-exceeded", pagesRequired: pages_required, pagesRemaining: pages_remaining };
}

/** Guest PDF over the free limit: the notice shown on the signup and login pages. */
export function guestPagesExceededNotice(required, remaining) {
  const left = remaining > 0 ? ` and you have ${pages(remaining)} left` : " and you have none left";
  return (
    `This statement is ${pages(required)}. Without an account you can scan ${pages(FREE_ANON_PAGES)} free${left}. ` +
    `Create a free account to get ${FREE_SIGNUP_PAGES} free pages and scan it.`
  );
}

/** Guest used all free pages: the notice shown on the signup and login pages. */
export const GUEST_TRIAL_USED_NOTICE =
  `You've used your ${FREE_ANON_PAGES} free guest pages. Create a free account to get ${FREE_SIGNUP_PAGES} more pages free.`;

/**
 * Signed-in scan over the page balance: message + what to buy next.
 * Subscribers top up with a page pack; everyone else subscribes (or buys the bulk pack).
 */
export function signedInPagesExceeded({ pages_required = 0, pages_remaining = 0 } = {}, subscribed) {
  const need =
    pages_required > 0
      ? `This scan needs ${pages(pages_required)} but you have ${pages_remaining > 0 ? `only ${pages(pages_remaining)}` : "no pages"} left.`
      : "You're out of pages.";
  if (subscribed) {
    return { message: `${need} Add a page pack to keep scanning. Pack pages never expire.`, cta: "Buy a page pack" };
  }
  return {
    message: `${need} Subscribe for ${PLAN_PAGES} pages a month at $${PLAN_PRICE}/mo, or buy ${BULK_PACK.pages} pages once for $${BULK_PACK.price}.`,
    cta: "Subscribe or buy pages",
  };
}
