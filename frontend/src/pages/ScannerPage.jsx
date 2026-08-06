import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import AppLayout from "../components/AppLayout";
import FileUpload from "../components/FileUpload";
import Loader from "../components/Loader";
import SummaryTable from "../components/SummaryTable";
import ResultsTable from "../components/ResultsTable";
import ChatPanel from "../components/ChatPanel";
import { useAuth } from "../contexts/AuthContext";
import { useUsage } from "../contexts/UsageContext";
import { processPdf, getJob, updateJobTransactions } from "../api/client";
import "./ScannerPage.css";

function ChatIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M18 6L6 18M6 6l12 12" />
    </svg>
  );
}

function parseAmount(amountStr) {
  const raw = String(amountStr ?? "0").replace(/,/g, "").trim();
  if (!raw) return 0;
  const num = Number.parseFloat(raw);
  if (Number.isNaN(num)) return 0;
  return Math.abs(num);
}

function computeSummaryByCategory(transactions) {
  const totals = {};
  for (const t of transactions || []) {
    const type = String(t.type || "").toLowerCase();
    const isDebit = type === "debit";
    const category = (t.category || "").trim() || "Other";
    let magnitude = parseAmount(t.amount);
    if (category === "Income") {
      if (isDebit) {
        magnitude = 0;
      }
    } else if (!isDebit) {
      magnitude = 0;
    }
    totals[category] = (totals[category] || 0) + magnitude;
  }
  return Object.entries(totals)
    .sort((a, b) => b[1] - a[1])
    .map(([category, total]) => ({ category, total }));
}

function escapeCsvValue(value) {
  const s = value == null ? "" : String(value);
  if (/[",\n]/.test(s)) {
    return `"${s.replace(/"/g, '""')}"`;
  }
  return s;
}

function transactionsToCsvBrowser(transactions) {
  const header = "date,description,amount,type,category";
  if (!transactions || transactions.length === 0) {
    return `${header}\n`;
  }
  const rows = transactions.map((t) =>
    [
      t.date ?? "",
      t.description ?? "",
      t.amount ?? "",
      t.type ?? "",
      t.category ?? "",
    ]
      .map(escapeCsvValue)
      .join(","),
  );
  return `${header}\n${rows.join("\n")}\n`;
}

export default function ScannerPage() {
  const { user } = useAuth();
  const { refreshUsage } = useUsage();
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
  const [conversionMode, setConversionMode] = useState("balanced");
  const [dataStatus, setDataStatus] = useState(null);
  const [trialCsvContent, setTrialCsvContent] = useState(null);
  const [outOfCredits, setOutOfCredits] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [pendingPasswordFile, setPendingPasswordFile] = useState(null);
  const [passwordError, setPasswordError] = useState(null);
  const [passwordInput, setPasswordInput] = useState("");
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
        } else {
          setError("Job not found");
        }
      })
      .catch((e) => setError(e.message || "Failed to load job"))
      .finally(() => setLoadingJob(false));
  }, [routeJobId, isLoggedIn]);

  const handleUpload = async (file) => {
    setError(null);
    setOutOfCredits(false);
    setDownloadError(null);
    setJobId(null);
    setTransactions([]);
    setSummaryByCategory([]);
    setCurrency(null);
    setDataStatus(null);
    setTrialCsvContent(null);
    setLoading(true);
    setLoadingFile({ name: file.name, size: file.size });
    try {
      const data = await processPdf(file, { incognitoMode, conversionMode });
      setJobId(data.job_id);
      setTransactions(data.transactions || []);
      setSummaryByCategory(data.summary_by_category || []);
      setCurrency(data.currency ?? null);
      setDataStatus(null);
      setTrialCsvContent(data.csv_content ?? null);
      refreshUsage();
    } catch (e) {
      if (e.isPdfPasswordRequired) {
        setPendingPasswordFile(file);
        setShowPasswordModal(true);
        setPasswordError(null);
        setPasswordInput("");
        setError(null);
        setJobId(null);
        setTransactions([]);
        setSummaryByCategory([]);
        setCurrency(null);
        setTrialCsvContent(null);
        setLoading(false);
        setLoadingFile(null);
        return;
      }
      if (e.insufficientCredits) {
        setOutOfCredits(true);
        setError("Out of credits. Add more to continue scanning.");
      } else {
        setError(e.message || "Upload failed");
      }
      setJobId(null);
      setDataStatus(null);
      setTransactions([]);
      setSummaryByCategory([]);
      setCurrency(null);
      setTrialCsvContent(null);
    } finally {
      setLoading(false);
      setLoadingFile(null);
    }
  };

  const handlePasswordSubmit = async (password) => {
    if (!pendingPasswordFile) return;
    setPasswordError(null);
    setLoading(true);
    setLoadingFile({ name: pendingPasswordFile.name, size: pendingPasswordFile.size });
    try {
      const data = await processPdf(pendingPasswordFile, {
        incognitoMode,
        conversionMode,
        password,
      });
      // Close modal and clear pending state first so the dialog always dismisses on success
      setShowPasswordModal(false);
      setPendingPasswordFile(null);
      setPasswordInput("");
      setPasswordError(null);
      // Then update results (optional chaining so we never throw and block the close)
      setJobId(data?.job_id ?? null);
      setTransactions(Array.isArray(data?.transactions) ? data.transactions : []);
      setSummaryByCategory(Array.isArray(data?.summary_by_category) ? data.summary_by_category : []);
      setCurrency(data?.currency ?? null);
      setDataStatus(null);
      setTrialCsvContent(data?.csv_content ?? null);
      refreshUsage();
    } catch (e) {
      if (e.isPdfPasswordIncorrect) {
        setPasswordError("Incorrect password. Please try again.");
      } else {
        setPasswordError(e.message || "Something went wrong.");
      }
    } finally {
      setLoading(false);
      setLoadingFile(null);
    }
  };

  const handlePasswordModalClose = () => {
    setShowPasswordModal(false);
    setPendingPasswordFile(null);
    setPasswordError(null);
    setPasswordInput("");
  };

  const hasResults = !!jobId;

  const handleTransactionChange = async (index, field, value) => {
    if (!Array.isArray(transactions) || index < 0 || index >= transactions.length) {
      return;
    }
    const nextTransactions = transactions.map((t, i) =>
      i === index ? { ...t, [field]: value } : t,
    );
    setTransactions(nextTransactions);

    // Update summary locally for immediate feedback
    setSummaryByCategory(computeSummaryByCategory(nextTransactions));

    // Keep CSV in sync for trial runs (unauthenticated)
    if (!isLoggedIn || trialCsvContent != null) {
      setTrialCsvContent(transactionsToCsvBrowser(nextTransactions));
    }

    // Persist changes for stored jobs (non-incognito / not purged)
    if (jobId && isLoggedIn && !dataStatus) {
      try {
        const updated = await updateJobTransactions(jobId, nextTransactions);
        setSummaryByCategory(
          (updated.summary_by_category || []).map((s) => ({
            category: s.category,
            total: s.total,
          })),
        );
      } catch (e) {
        // Surface the error alongside other scanner alerts
        setError(e.message || "Failed to save changes");
      }
    }
  };

  /** Replace a single transaction (e.g. from the edit card). Updates table, summary, CSV, and API in one go. */
  const handleSaveTransaction = async (index, transaction) => {
    if (!Array.isArray(transactions) || index < 0 || index >= transactions.length) {
      return;
    }
    const nextTransactions = transactions.map((t, i) =>
      i === index ? { ...t, ...transaction } : t,
    );
    setTransactions(nextTransactions);
    setSummaryByCategory(computeSummaryByCategory(nextTransactions));

    if (!isLoggedIn || trialCsvContent != null) {
      setTrialCsvContent(transactionsToCsvBrowser(nextTransactions));
    }

    if (jobId && isLoggedIn && !dataStatus) {
      try {
        const updated = await updateJobTransactions(jobId, nextTransactions);
        setSummaryByCategory(
          (updated.summary_by_category || []).map((s) => ({
            category: s.category,
            total: s.total,
          })),
        );
      } catch (e) {
        setError(e.message || "Failed to save changes");
      }
    }
  };

  return (
    <AppLayout>
      <div className="scanner-page">
        <div className="scanner-head">
          <h1 className="scanner-title">Process statement</h1>
          <p className="scanner-subtitle">Upload a PDF or open a past job from your dashboard.</p>
        </div>

        <div className="scanner-main">
        <div className="scanner-upload-card">
          <div className="scanner-conversion-mode">
            <label htmlFor="conversion-mode" className="scanner-conversion-mode-label">Conversion mode</label>
            <select
              id="conversion-mode"
              value={conversionMode}
              onChange={(e) => setConversionMode(e.target.value)}
              disabled={loading}
              className="scanner-conversion-mode-select"
              aria-describedby="conversion-mode-hint"
            >
              <option value="fast">Fast — lowest latency, simple documents</option>
              <option value="balanced">Balanced — speed and accuracy (recommended)</option>
              <option value="accurate">Accurate — best for complex layouts and tables</option>
            </select>
           
          </div>
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
                {outOfCredits && (
                  <>
                    {" "}
                    <button type="button" className="scanner-alert-link" onClick={() => navigate("/settings")}>
                      Add credits
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
          <>
            <div className="scanner-results">
              <div className="scanner-results-tables">
                <SummaryTable summaryByCategory={summaryByCategory} currency={currency} />
                <ResultsTable
                  transactions={transactions}
                  jobId={jobId}
                  csvContent={trialCsvContent}
                  onDownloadError={setDownloadError}
                  onTransactionChange={handleTransactionChange}
                  onSaveTransaction={handleSaveTransaction}
                />
              </div>
            </div>

            <div className="scanner-fab-wrap">
              <button
                type="button"
                className="scanner-fab"
                onClick={() => setChatOpen(true)}
                aria-label="Open Validate CSV chat"
                title="Validate using AI"
              >
                <span className="scanner-fab-icon" aria-hidden>
                  <ChatIcon />
                </span>
                <span className="scanner-fab-tooltip">
                  <span className="scanner-fab-tooltip-text-full">Validate CSV – Ask about your transactions and categories</span>
                  <span className="scanner-fab-tooltip-text-mobile">Validate using AI</span>
                </span>
              </button>
            </div>

            {chatOpen && (
              <div className="scanner-chat-drawer-backdrop" onClick={() => setChatOpen(false)} aria-hidden />
            )}
            <div className={`scanner-chat-drawer ${chatOpen ? "scanner-chat-drawer--open" : ""}`}>
              <div className="scanner-chat-drawer-inner">
                <div className="scanner-chat-drawer-header">
                  <h2 className="scanner-chat-drawer-title">Validate CSV</h2>
                  <button
                    type="button"
                    className="scanner-chat-drawer-close"
                    onClick={() => setChatOpen(false)}
                    aria-label="Close chat"
                  >
                    <CloseIcon />
                  </button>
                </div>
                <ChatPanel
                  key={jobId}
                  jobId={jobId}
                  disabled={!jobId}
                  requireLogin={!isLoggedIn}
                  onRequireLogin={() => navigate("/login")}
                  hideHeading
                />
              </div>
            </div>
          </>
        )}
        </div>
      </div>

      {showPasswordModal && (
        <div className="scanner-password-modal-backdrop" onClick={handlePasswordModalClose} aria-hidden />
      )}
      {showPasswordModal && (
        <div className="scanner-password-modal" role="dialog" aria-labelledby="pdf-password-title" aria-modal="true">
          <h2 id="pdf-password-title" className="scanner-password-modal-title">PDF is password protected</h2>
          <p className="scanner-password-modal-desc">Enter the password to unlock and process this file.</p>
          {passwordError && (
            <p className="scanner-password-modal-error" role="alert">{passwordError}</p>
          )}
          <form
            className="scanner-password-modal-form"
            onSubmit={(e) => {
              e.preventDefault();
              handlePasswordSubmit(passwordInput);
            }}
          >
            <label htmlFor="pdf-password-input" className="scanner-password-modal-label">
              Password
            </label>
            <input
              id="pdf-password-input"
              type="password"
              className="scanner-password-modal-input"
              value={passwordInput}
              onChange={(e) => setPasswordInput(e.target.value)}
              placeholder="Enter PDF password"
              autoComplete="current-password"
              disabled={loading}
              autoFocus
            />
            <div className="scanner-password-modal-actions">
              <button type="button" className="scanner-password-modal-btn secondary" onClick={handlePasswordModalClose} disabled={loading}>
                Cancel
              </button>
              <button type="submit" className="scanner-password-modal-btn primary" disabled={loading || !passwordInput.trim()}>
                {loading ? "Unlocking…" : "Unlock"}
              </button>
            </div>
          </form>
        </div>
      )}
    </AppLayout>
  );
}
