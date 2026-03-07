import { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import AppLayout from "../components/AppLayout";
import FileUpload from "../components/FileUpload";
import Loader from "../components/Loader";
import SummaryTable from "../components/SummaryTable";
import ResultsTable from "../components/ResultsTable";
import ChatPanel from "../components/ChatPanel";
import { processPdf, getJob } from "../api/client";
import "./ScannerPage.css";

export default function ScannerPage() {
  const { jobId: routeJobId } = useParams();
  const [jobId, setJobId] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [summaryByCategory, setSummaryByCategory] = useState([]);
  const [currency, setCurrency] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadingFile, setLoadingFile] = useState(null);
  const [loadingJob, setLoadingJob] = useState(!!routeJobId);
  const [error, setError] = useState(null);
  const [downloadError, setDownloadError] = useState(null);

  // Load existing job when opening from dashboard (e.g. /scanner/:jobId)
  useEffect(() => {
    if (!routeJobId) return;
    setError(null);
    setLoadingJob(true);
    getJob(routeJobId)
      .then((data) => {
        if (data) {
          setJobId(data.job_id);
          setTransactions(data.transactions || []);
          setSummaryByCategory((data.summary_by_category || []).map((s) => ({ category: s.category, total: s.total })));
          setCurrency(data.currency ?? null);
        } else {
          setError("Job not found");
        }
      })
      .catch((e) => setError(e.message || "Failed to load job"))
      .finally(() => setLoadingJob(false));
  }, [routeJobId]);

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
    <AppLayout>
      <div className="scanner-page">
        <div className="scanner-head">
          <h1 className="scanner-title">Process statement</h1>
          <p className="scanner-subtitle">Upload a PDF or open a past job from your dashboard.</p>
        </div>

        <div className="scanner-main">
        <div className="scanner-upload-card">
          <FileUpload onUpload={handleUpload} disabled={loading} />
        </div>

        {loading && (
          <Loader
            fileName={loadingFile?.name}
            fileSize={loadingFile?.size}
          />
        )}

        {loadingJob && (
          <div className="scanner-loading-job">Loading job…</div>
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
        </div>
      </div>
    </AppLayout>
  );
}
