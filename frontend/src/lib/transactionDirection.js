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

/** Whether a transaction passes the active filter (a category name or a direction filter). */
export function matchesFilter(t, filter) {
  if (!filter) return true;
  if (filter === CREDIT_FILTER) return getDirection(t) === "credit";
  if (filter === DEBIT_FILTER) return getDirection(t) === "debit";
  // Blank categories are grouped as "Other" in the summary, so match that.
  return ((t.category || "").trim() || "Other") === filter;
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
