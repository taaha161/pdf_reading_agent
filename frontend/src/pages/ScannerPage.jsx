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

const SCANNED_METHOD = { OCR: "ocr", VISION: "vision" };

export default function ScannerPage() {
  const [jobId, setJobId] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [summaryByCategory, setSummaryByCategory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [loadingFile, setLoadingFile] = useState(null);
  const [error, setError] = useState(null);
  const [downloadError, setDownloadError] = useState(null);
  const [scannedMethod, setScannedMethod] = useState(SCANNED_METHOD.VISION);

  const handleUpload = async (file) => {
    setError(null);
    setDownloadError(null);
    setLoading(true);
    setLoadingFile({ name: file.name, size: file.size });
    try {
      const data = await processPdf(file, { scannedMethod });
      setJobId(data.job_id);
      setTransactions(data.transactions || []);
      setSummaryByCategory(data.summary_by_category || []);
    } catch (e) {
      setError(e.message || "Upload failed");
      setJobId(null);
      setTransactions([]);
      setSummaryByCategory([]);
    } finally {
      setLoading(false);
      setLoadingFile(null);
    }
  };

  const hasResults = summaryByCategory?.length > 0 || transactions?.length > 0;

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
          <div className="scanned-method-toggle">
            <span className="scanned-method-label">For scanned PDFs use:</span>
            <div className="scanned-method-options" role="group" aria-label="Scanned PDF method">
              <label className={scannedMethod === SCANNED_METHOD.OCR ? "active" : ""}>
                <input
                  type="radio"
                  name="scanned_method"
                  value={SCANNED_METHOD.OCR}
                  checked={scannedMethod === SCANNED_METHOD.OCR}
                  onChange={() => setScannedMethod(SCANNED_METHOD.OCR)}
                  disabled={loading}
                />
                OCR
              </label>
              <label className={scannedMethod === SCANNED_METHOD.VISION ? "active" : ""}>
                <input
                  type="radio"
                  name="scanned_method"
                  value={SCANNED_METHOD.VISION}
                  checked={scannedMethod === SCANNED_METHOD.VISION}
                  onChange={() => setScannedMethod(SCANNED_METHOD.VISION)}
                  disabled={loading}
                />
                AI image capture
              </label>
            </div>
          </div>
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
              <SummaryTable summaryByCategory={summaryByCategory} />
              <ResultsTable
                transactions={transactions}
                jobId={jobId}
                onDownloadError={setDownloadError}
              />
            </div>
            <aside className="scanner-results-chat">
              <ChatPanel jobId={jobId} disabled={!jobId} />
            </aside>
          </div>
        )}
      </main>
    </div>
  );
}
