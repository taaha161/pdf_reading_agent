// Money direction of a transaction, and the "All credits" / "All debits" summary filters.
// Filter values share the category-filter state, so they use keys no real category can have.

export const CREDIT_FILTER = "__credits__";
export const DEBIT_FILTER = "__debits__";

const FILTER_LABELS = {
  [CREDIT_FILTER]: "Credits (money in)",
  [DEBIT_FILTER]: "Debits (money out)",
};

/** "credit" (money added), "debit" (money deducted), or null if unknown. */
export function getDirection(t) {
  const type = String(t?.type || "").toLowerCase();
  if (type === "credit" || type === "debit") return type;
  const amount = String(t?.amount ?? "").trim();
  if (amount.startsWith("-")) return "debit";
  if (amount.startsWith("+")) return "credit";
  return null;
}

export function isDirectionFilter(filter) {
  return filter === CREDIT_FILTER || filter === DEBIT_FILTER;
}

export function filterLabel(filter) {
  return FILTER_LABELS[filter] ?? filter;
}

// A category with both money in and money out gets a second summary row with one of
// these suffixes (mirrors backend/services/summary.py).
export const MONEY_IN_SUFFIX = " (money in)";
export const MONEY_OUT_SUFFIX = " (money out)";

function categoryOf(t) {
  // Blank categories are grouped as "Other" in the summary, so match that.
  return (t.category || "").trim() || "Other";
}

/** Whether a transaction passes the active filter (a category name or a direction filter). */
export function matchesFilter(t, filter) {
  if (!filter) return true;
  if (filter === CREDIT_FILTER) return getDirection(t) === "credit";
  if (filter === DEBIT_FILTER) return getDirection(t) === "debit";
  const cat = categoryOf(t);
  if (cat === filter) return true;
  // "<category> (money in)" / "(money out)" rows: that category, one direction only.
  if (filter === cat + MONEY_IN_SUFFIX) return getDirection(t) !== "debit";
  if (filter === cat + MONEY_OUT_SUFFIX) return getDirection(t) === "debit";
  return false;
}

/**
 * Category totals, same rules as the backend summary: each category's main row sums its
 * primary direction (credits for Income and credit-only categories, debits otherwise);
 * the other direction, if present, gets its own suffixed row so no money is dropped.
 */
export function summaryByCategory(transactions) {
  const debits = {};
  const credits = {};
  for (const t of transactions || []) {
    const n = Math.abs(Number.parseFloat(String(t.amount ?? "").replace(/[^0-9.-]/g, "")));
    const amount = Number.isFinite(n) ? n : 0;
    const bucket = String(t.type || "").toLowerCase() === "debit" ? debits : credits;
    const cat = categoryOf(t);
    bucket[cat] = (bucket[cat] || 0) + amount;
  }
  const totals = {};
  for (const cat of new Set([...Object.keys(debits), ...Object.keys(credits)])) {
    const creditPrimary = cat === "Income" || !(cat in debits);
    if (creditPrimary) {
      totals[cat] = credits[cat] || 0;
      if (cat in debits) totals[cat + MONEY_OUT_SUFFIX] = debits[cat];
    } else {
      totals[cat] = debits[cat];
      if (cat in credits) totals[cat + MONEY_IN_SUFFIX] = credits[cat];
    }
  }
  return Object.entries(totals)
    .sort((a, b) => b[1] - a[1])
    .map(([category, total]) => ({ category, total }));
}

/** Sum of absolute amounts for credits and debits. */
export function directionTotals(transactions) {
  let credit = 0;
  let debit = 0;
  for (const t of transactions || []) {
    const n = Math.abs(Number.parseFloat(String(t.amount ?? "").replace(/[^0-9.-]/g, "")));
    if (!Number.isFinite(n)) continue;
    const dir = getDirection(t);
    if (dir === "credit") credit += n;
    else if (dir === "debit") debit += n;
  }
  return { credit, debit };
}
