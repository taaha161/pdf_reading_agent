import { downloadCsv } from "../api/client";
import "./ResultsTable.css";

export default function ResultsTable({ transactions, jobId, onDownloadError }) {
  if (!transactions?.length) return null;

  const handleDownload = async () => {
    try {
      await downloadCsv(jobId);
    } catch (e) {
      onDownloadError?.(e.message);
    }
  };

  return (
    <section className="results-section">
      <div className="results-header">
        <h2>Transactions</h2>
        <button type="button" onClick={handleDownload} className="download-btn">
          Download CSV
        </button>
      </div>
      <div className="table-wrap">
        <table className="results-table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Description</th>
              <th>Amount</th>
              <th>Type</th>
              <th>Category</th>
            </tr>
          </thead>
          <tbody>
            {transactions.map((t, i) => (
              <tr key={i}>
                <td>{t.date}</td>
                <td>{t.description}</td>
                <td>{t.amount}</td>
                <td>{t.type}</td>
                <td>{t.category}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
