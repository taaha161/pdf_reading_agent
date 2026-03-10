import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import AppLayout from "../components/AppLayout";
import FileUpload from "../components/FileUpload";
import Loader from "../components/Loader";
import SummaryTable from "../components/SummaryTable";
import ResultsTable from "../components/ResultsTable";
import ChatPanel from "../components/ChatPanel";
import { useAuth } from "../contexts/AuthContext";
import { processPdf, getJob } from "../api/client";
import "./ScannerPage.css";

export default function ScannerPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
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
  const [incognitoMode, setIncognitoMode] = useState(false);
  const [dataStatus, setDataStatus] = useState(null);
  const [trialCsvContent, setTrialCsvContent] = useState(null);
  const [trialRawText, setTrialRawText] = useState(null);
  const isLoggedIn = !!user;

  // Load existing job when opening from dashboard (e.g. /scanner/:jobId)
  useEffect(() => {
    if (!routeJobId) return;
    if (!isLoggedIn) {
      setError("Sign in to view this job.");
      setLoadingJob(false);
      return;
    }
    setError(null);
    setLoadingJob(true);
    getJob(routeJobId)
      .then((data) => {
        if (data) {
          setJobId(data.job_id);
          setTransactions(data.transactions || []);
          setSummaryByCategory((data.summary_by_category || []).map((s) => ({ category: s.category, total: s.total })));
          setCurrency(data.currency ?? null);
          setDataStatus(data.data_status ?? null);
          setTrialCsvContent(null);
          setTrialRawText(null);
        } else {
          setError("Job not found");
        }
      })
      .catch((e) => setError(e.message || "Failed to load job"))
      .finally(() => setLoadingJob(false));
  }, [routeJobId, isLoggedIn]);

  const handleUpload = async (file) => {
    setError(null);
    setDownloadError(null);
    setJobId(null);
    setTransactions([]);
    setSummaryByCategory([]);
    setCurrency(null);
    setDataStatus(null);
    setTrialCsvContent(null);
    setTrialRawText(null);
    setLoading(true);
    setLoadingFile({ name: file.name, size: file.size });
    try {
      const data = await processPdf(file, { incognitoMode });
      setJobId(data.job_id);
      setTransactions(data.transactions || []);
      setSummaryByCategory(data.summary_by_category || []);
      setCurrency(data.currency ?? null);
      setDataStatus(null);
      setTrialCsvContent(data.csv_content ?? null);
      setTrialRawText(data.raw_text ?? null);
    } catch (e) {
      setError(e.message || "Upload failed");
      setJobId(null);
      setDataStatus(null);
      setTransactions([]);
      setSummaryByCategory([]);
      setCurrency(null);
      setTrialCsvContent(null);
      setTrialRawText(null);
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
          {isLoggedIn && (
            <>
              <label className="scanner-incognito">
                <input
                  type="checkbox"
                  checked={incognitoMode}
                  onChange={(e) => setIncognitoMode(e.target.checked)}
                  disabled={loading}
                />
                <span>Incognito mode</span>
              </label>
              <p className="scanner-incognito-hint">Do not store transaction data, currency, or raw text (job count is still recorded).</p>
            </>
          )}
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
            {error && (
              <p className="scanner-alert error">
                {error}
                {error.includes("Trial limit") && (
                  <>
                    {" "}
                    <button type="button" className="scanner-alert-link" onClick={() => navigate("/login")}>
                      Log in to process more
                    </button>
                  </>
                )}
              </p>
            )}
            {downloadError && <p className="scanner-alert error">{downloadError}</p>}
          </div>
        )}

        {hasResults && dataStatus && (
          <div className="scanner-data-status" role="status">
            {dataStatus === "incognito"
              ? "This job was run in incognito mode. No transaction data, currency, or raw text was stored."
              : "Data for this job was deleted. Transaction data, currency, and raw text are no longer available."}
          </div>
        )}

        {hasResults && (
          <div className="scanner-results">
            <div className="scanner-results-tables">
              <SummaryTable summaryByCategory={summaryByCategory} currency={currency} />
              <ResultsTable
                transactions={transactions}
                jobId={jobId}
                csvContent={trialCsvContent}
                rawText={trialRawText}
                onDownloadError={setDownloadError}
              />
            </div>
            <aside className="scanner-results-chat">
              {isLoggedIn ? (
                <ChatPanel key={jobId} jobId={jobId} disabled={!jobId} />
              ) : (
                <p className="scanner-trial-chat-hint">Sign in to save this job and chat about it.</p>
              )}
            </aside>
          </div>
        )}
        </div>
      </div>
    </AppLayout>
  );
}
