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

export default function SummaryTable({ summaryByCategory, currency }) {
  if (!summaryByCategory?.length) return null;

  return (
    <section className="summary-section">
      <h2>Summary by category</h2>
      <div className="table-wrap">
        <table className="summary-table">
          <thead>
            <tr>
              <th>Category</th>
              <th className="amount-col">Total</th>
            </tr>
          </thead>
          <tbody>
            {summaryByCategory.map((row, i) => (
              <tr key={i}>
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
