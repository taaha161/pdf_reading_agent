import { useState } from "react";
import { Link } from "react-router-dom";
import logo from "../assets/pdf_to_excel_logo.png";
import FileUpload from "../components/FileUpload";
import Loader from "../components/Loader";
import SummaryTable from "../components/SummaryTable";
import ResultsTable from "../components/ResultsTable";
import ChatPanel from "../components/ChatPanel";
import { processPdf } from "../api/client";
import "./ScannerPage.css";

export default function ScannerPage() {
  const [jobId, setJobId] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [summaryByCategory, setSummaryByCategory] = useState([]);
  const [currency, setCurrency] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadingFile, setLoadingFile] = useState(null);
  const [error, setError] = useState(null);
  const [downloadError, setDownloadError] = useState(null);

  const handleUpload = async (file) => {
    setError(null);
    setDownloadError(null);
    setJobId(null);
    setTransactions([]);
    setSummaryByCategory([]);
    setCurrency(null);
    setLoading(true);
    setLoadingFile({ name: file.name, size: file.size });
    try {
      const data = await processPdf(file);
      setJobId(data.job_id);
      setTransactions(data.transactions || []);
      setSummaryByCategory(data.summary_by_category || []);
      setCurrency(data.currency ?? null);
    } catch (e) {
      setError(e.message || "Upload failed");
      setJobId(null);
      setTransactions([]);
      setSummaryByCategory([]);
      setCurrency(null);
    } finally {
      setLoading(false);
      setLoadingFile(null);
    }
  };

  const hasResults = !!jobId;

  return (
    <div className="scanner-page">
      <header className="scanner-header">
        <Link to="/" className="scanner-back">
          ← Back to home
        </Link>
        <div className="scanner-brand">
          <img src={logo} alt="" className="scanner-logo" aria-hidden />
          <h1 className="scanner-title">Bank Statement Processor</h1>
        </div>
      </header>

      <main className="scanner-main">
        <div className="scanner-upload-card">
          <FileUpload onUpload={handleUpload} disabled={loading} />
        </div>

        {loading && (
          <Loader
            fileName={loadingFile?.name}
            fileSize={loadingFile?.size}
          />
        )}

        {(error || downloadError) && (
          <div className="scanner-alerts" role="alert">
            {error && <p className="scanner-alert error">{error}</p>}
            {downloadError && <p className="scanner-alert error">{downloadError}</p>}
          </div>
        )}

        {hasResults && (
          <div className="scanner-results">
            <div className="scanner-results-tables">
              <SummaryTable summaryByCategory={summaryByCategory} currency={currency} />
              <ResultsTable
                transactions={transactions}
                jobId={jobId}
                onDownloadError={setDownloadError}
              />
            </div>
            <aside className="scanner-results-chat">
              <ChatPanel key={jobId} jobId={jobId} disabled={!jobId} />
            </aside>
          </div>
        )}
      </main>
    </div>
  );
}
