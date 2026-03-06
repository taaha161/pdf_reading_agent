import { downloadCsv, downloadMarkdown } from "../api/client";
import "./ResultsTable.css";

export default function ResultsTable({ transactions, jobId, onDownloadError }) {
  if (!jobId) return null;

  const handleDownloadCsv = async () => {
    try {
      await downloadCsv(jobId);
    } catch (e) {
      onDownloadError?.(e.message);
    }
  };

  const handleDownloadMarkdown = async () => {
    try {
      await downloadMarkdown(jobId);
    } catch (e) {
      onDownloadError?.(e.message);
    }
  };

  return (
    <section className="results-section">
      <div className="results-header">
        <h2>Transactions</h2>
        <div className="results-header-actions">
          <button type="button" onClick={handleDownloadMarkdown} className="download-btn download-btn-secondary">
            Download markdown
          </button>
          {transactions?.length > 0 && (
            <button type="button" onClick={handleDownloadCsv} className="download-btn">
              Download CSV
            </button>
          )}
        </div>
      </div>
      {transactions?.length > 0 ? (
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
      ) : (
        <p className="results-empty">No transactions extracted. Download the markdown to check if the PDF was converted correctly.</p>
      )}
    </section>
  );
}
