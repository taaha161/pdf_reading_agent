import "./SummaryTable.css";

function formatCurrency(value) {
  const n = Number(value);
  if (Number.isNaN(n)) return value;
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(n);
}

export default function SummaryTable({ summaryByCategory }) {
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
                <td className="amount-col">{formatCurrency(row.total)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
