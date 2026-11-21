// Map common currency names to ISO 4217 codes for Intl.NumberFormat
const CURRENCY_CODE_MAP = {
  "pakistan rupee": "PKR",
  "pkr": "PKR",
  "us dollar": "USD",
  "usd": "USD",
  "euro": "EUR",
  "eur": "EUR",
  "gbp": "GBP",
  "british pound": "GBP",
  "inr": "INR",
  "indian rupee": "INR",
};

/** Amount with the statement's currency symbol when we know it, else a plain 2-decimal number. */
export function formatMoney(value, currency) {
  const n = Number(value);
  if (Number.isNaN(n)) return String(value);
  if (!currency || !currency.trim()) {
    return new Intl.NumberFormat("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(n);
  }
  const key = currency.trim().toLowerCase();
  const code = CURRENCY_CODE_MAP[key] || (key.length === 3 ? key.toUpperCase() : null);
  if (!code) {
    return new Intl.NumberFormat("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(n);
  }
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: code,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(n);
}
