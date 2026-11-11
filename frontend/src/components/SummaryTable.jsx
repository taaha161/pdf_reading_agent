import DownloadMenu from "./DownloadMenu";
import { CREDIT_FILTER, DEBIT_FILTER, directionTotals } from "../lib/transactionDirection";
import "./SummaryTable.css";

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

function formatTotal(value, currency) {
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

export default function SummaryTable({
  summaryByCategory,
  currency,
  activeCategory = null,
  onSelectCategory,
  transactions,
  onDownloadError,
}) {
  if (!summaryByCategory?.length) return null;
  const totals = directionTotals(transactions);

  const interactive = typeof onSelectCategory === "function";
  const select = (category) => {
    if (!interactive) return;
    // Clicking the active category again toggles back to "All".
    onSelectCategory(category === activeCategory ? null : category);
  };
  const rowProps = (category) =>
    interactive
      ? {
          className: `summary-row--clickable${category === activeCategory ? " summary-row--active" : ""}`,
          onClick: () => select(category),
          onKeyDown: (e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              select(category);
            }
          },
          tabIndex: 0,
          role: "button",
          "aria-pressed": category === activeCategory,
        }
      : {};

  return (
    <section className="summary-section" data-clarity-mask="true">
      <div className="summary-header">
        <h2>Summary by category</h2>
        {transactions?.length > 0 && (
          <DownloadMenu transactions={transactions} onError={onDownloadError} kind="summary" />
        )}
      </div>
      {interactive && (
        <p className="summary-hint">Click a category to filter transactions.</p>
      )}
      <div className="table-wrap">
        <table className="summary-table">
          <thead>
            <tr>
              <th>Category</th>
              <th className="amount-col">Total</th>
            </tr>
          </thead>
          <tbody>
            {interactive && (
              <tr {...rowProps(null)} aria-label="Show all categories">
                <td>All</td>
                <td className="amount-col" />
              </tr>
            )}
            <tr {...rowProps(CREDIT_FILTER)} aria-label={interactive ? "Filter by credits (money in)" : undefined}>
              <td className="summary-direction summary-direction--credit">Credits (money in)</td>
              <td className="amount-col summary-direction--credit">{formatTotal(totals.credit, currency)}</td>
            </tr>
            <tr
              {...rowProps(DEBIT_FILTER)}
              className={`${rowProps(DEBIT_FILTER).className ?? ""} summary-row--direction-end`.trim()}
              aria-label={interactive ? "Filter by debits (money out)" : undefined}
            >
              <td className="summary-direction summary-direction--debit">Debits (money out)</td>
              <td className="amount-col summary-direction--debit">{formatTotal(totals.debit, currency)}</td>
            </tr>
            {summaryByCategory.map((row, i) => (
              <tr key={row.category ?? i} {...rowProps(row.category)} aria-label={interactive ? `Filter by ${row.category}` : undefined}>
                <td>{row.category}</td>
                <td className="amount-col">{formatTotal(row.total, currency)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
