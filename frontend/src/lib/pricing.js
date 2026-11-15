// Page-based pricing. Mirrors backend services/billing.py — keep in sync.
export const FREE_ANON_PAGES = 10; // without an account
export const FREE_SIGNUP_PAGES = 100; // free for the first month after signup
export const FREE_SIGNUP_DAYS = 30;
export const PLAN_PAGES = 100; // per month on the paid plan
export const PLAN_PRICE = 10; // USD / month
export const ACCURATE_MULTIPLIER = 2; // High accuracy mode uses 2 pages per PDF page

// Page packs: never expire, any signed-in user can buy.
export const PAGE_PACKS = [
  { id: "10", pages: 10, price: 2 },
  { id: "30", pages: 30, price: 5 },
  { id: "100", pages: 100, price: 10 },
];

/** "May 3" style date for a free-month expiry. */
export function formatExpiry(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "" : d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}
