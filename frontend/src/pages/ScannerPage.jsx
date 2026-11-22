import { useState, useEffect, useRef, useCallback } from "react";
import { ACCURATE_MULTIPLIER, FREE_ANON_PAGES, FREE_SIGNUP_PAGES } from "../lib/pricing";
import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import AppLayout from "../components/AppLayout";
import FileUpload from "../components/FileUpload";
import Loader from "../components/Loader";
import SummaryTable from "../components/SummaryTable";
import ResultsTable from "../components/ResultsTable";
import ReconciliationPanel from "../components/ReconciliationPanel";
import ChatPanel from "../components/ChatPanel";
import EmailSpreadsheet from "../components/EmailSpreadsheet";
import FeedbackPrompt from "../components/FeedbackPrompt";
import { useAuth } from "../contexts/AuthContext";
import { useUsage } from "../contexts/UsageContext";
import { runScan, getJob, updateJobTransactions } from "../api/client";
import "./ScannerPage.css";
import PasswordInput from "../components/PasswordInput";
import { handOffFile, takeHandedOffFile } from "../lib/fileHandoff";
import { trackEvent } from "../lib/analytics";
import { fileTooLarge, formatMB, maxFileBytes, MAX_FILE_BYTES_SIGNED_IN, MB } from "../lib/fileSize";
import { trackLinkedInConversion, LINKEDIN_TRIAL_SCAN_CONVERSION_ID } from "../lib/linkedinConversions";
import sampleStatement from "../lib/sampleStatement.json";
import { isDirectionFilter, summaryByCategory as computeSummaryByCategory } from "../lib/transactionDirection";

/** The sample statement prints no running balances, but its summary box is known and adds up. */
function sampleReconciliation() {
  const { opening, closing, credits, debits } = sampleStatement;
  const check = (key, value) => ({ key, status: "pass", expected: value, actual: value, difference: 0 });
  return {
    status: "reconciled",
    reason: null,
    opening_balance: opening,
    closing_balance: closing,
    total_credits: credits,
    total_debits: debits,
    checks: [check("opening", opening), check("credits", credits), check("debits", debits), check("closing", closing)],
    hints: [],
  };
}

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

function pushDataLayer(data) {
  try {
    (window.dataLayer = window.dataLayer || []).push(data);
  } catch {
    /* analytics must never break the scanner */
  }
}

function escapeCsvValue(value) {
  const s = value == null ? "" : String(value);
  if (/[",\n]/.test(s)) {
    return `"${s.replace(/"/g, '""')}"`;
  }
  return s;
}

function transactionsToCsvBrowser(transactions) {
  const header = "date,description,amount,type,category,balance";
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
      t.balance ?? "",
    ]
      .map(escapeCsvValue)
      .join(","),
  );
  return `${header}\n${rows.join("\n")}\n`;
}

/** Placeholder job id for the built-in sample statement (never sent to the API). */
const SAMPLE_JOB_ID = "sample";

/** Normalize a row for matching chat answers back to table rows. */
const rowKey = (t) =>
  [
    String(t?.date ?? "").trim(),
    String(t?.description ?? "").trim().toLowerCase().replace(/\s+/g, " "),
    (() => {
      const n = Math.abs(parseFloat(String(t?.amount ?? "").replace(/[^0-9.-]/g, "")));
      return Number.isFinite(n) ? n.toFixed(2) : "";
    })(),
  ].join("|");

/** Indices of `transactions` that the chat answer's rows refer to (each table row used once). */
function matchRowIndices(transactions, rows) {
  const byKey = new Map();
  (transactions || []).forEach((t, i) => {
    const k = rowKey(t);
    if (!byKey.has(k)) byKey.set(k, []);
    byKey.get(k).push(i);
  });
  const out = new Set();
  for (const r of rows) {
    const list = byKey.get(rowKey(r));
    if (list?.length) out.add(list.shift());
  }
  return out;
}

const TRIAL_LIMIT_NOTICE = `You've used your ${FREE_ANON_PAGES} free pages. Create a free account to get ${FREE_SIGNUP_PAGES} free pages for your first month.`;
const CHAT_NOTICE = `Create a free account to ask questions about your statement. Your first month includes ${FREE_SIGNUP_PAGES} pages free.`;
const FILE_SIZE_NOTICE = `Free accounts can upload PDFs up to ${formatMB(MAX_FILE_BYTES_SIGNED_IN)}.`;

const FEEDBACK_SCAN_COUNT_KEY = "bss_scan_count";
const FEEDBACK_PROMPTED_KEY = "bss_feedback_prompted";
const FEEDBACK_AFTER_SCANS = 2;
const FEEDBACK_DELAY_MS = 4000;

/** Count successful scans in this browser; true when the feedback prompt is due (2nd scan, never shown before). */
function noteScanForFeedback() {
  try {
    const count = Number(localStorage.getItem(FEEDBACK_SCAN_COUNT_KEY) || 0) + 1;
    localStorage.setItem(FEEDBACK_SCAN_COUNT_KEY, String(count));
    return count >= FEEDBACK_AFTER_SCANS && !localStorage.getItem(FEEDBACK_PROMPTED_KEY);
  } catch {
    return false;
  }
}

function markFeedbackPrompted() {
  try {
    localStorage.setItem(FEEDBACK_PROMPTED_KEY, "1");
  } catch {
    /* storage blocked: prompt may show again next time, which is harmless */
  }
}

export default function ScannerPage() {
  const { user, loading: authLoading } = useAuth();
  const { usage, refreshUsage, applyUsage } = useUsage();
  const navigate = useNavigate();
  const { jobId: routeJobId } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const [jobId, setJobId] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [summaryByCategory, setSummaryByCategory] = useState([]);
  const [reconciliation, setReconciliation] = useState(null);
  // Trial edits aren't sent to the server, so the check can't be recomputed for them.
  const [reconciliationStale, setReconciliationStale] = useState(false);
  const [categoryFilter, setCategoryFilter] = useState(null);
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
  const [tooLargeUpgrade, setTooLargeUpgrade] = useState(null); // "signup" | "subscribe" | null
  const [chatOpen, setChatOpen] = useState(false);
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [pendingPasswordFile, setPendingPasswordFile] = useState(null);
  const [passwordError, setPasswordError] = useState(null);
  const [passwordInput, setPasswordInput] = useState("");
  const [checkingPassword, setCheckingPassword] = useState(false);
  const [scanProgress, setScanProgress] = useState(null);
  const [emailPopupOpen, setEmailPopupOpen] = useState(false);
  const emailPopupShownFor = useRef(null);
  const [feedbackDue, setFeedbackDue] = useState(false);
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const isLoggedIn = !!user;
  const isGuest = !authLoading && !isLoggedIn;
  const isSample = jobId === SAMPLE_JOB_ID;

  // Funnel top: one view event per page load once we know who's here, so
  // GA can compare scanner_view → scan_started → scan_completed (by logged_in).
  const viewTracked = useRef(false);
  // New scan / job → reset category filter to "All".
  useEffect(() => {
    setCategoryFilter(null);
  }, [jobId]);

  useEffect(() => {
    if (authLoading || viewTracked.current) return;
    viewTracked.current = true;
    pushDataLayer({ event: "scanner_view", logged_in: isLoggedIn });
  }, [authLoading, isLoggedIn]);
  const canEmailSpreadsheet = !isLoggedIn && !!jobId && !isSample && !!trialCsvContent && transactions.length > 0;

  // Anonymous trial: pop up "Email me this spreadsheet" shortly after results load (once per scan).
  useEffect(() => {
    if (!canEmailSpreadsheet || emailPopupShownFor.current === jobId) return;
    const timer = setTimeout(() => {
      emailPopupShownFor.current = jobId;
      setEmailPopupOpen(true);
    }, 1500);
    return () => clearTimeout(timer);
  }, [canEmailSpreadsheet, jobId]);

  // Optional feedback prompt: a few seconds after the 2nd successful scan's results load,
  // once per browser, and never on top of another popup.
  useEffect(() => {
    if (!feedbackDue || !jobId || emailPopupOpen || showPasswordModal) return;
    const timer = setTimeout(() => {
      markFeedbackPrompted();
      setFeedbackDue(false);
      setFeedbackOpen(true);
    }, FEEDBACK_DELAY_MS);
    return () => clearTimeout(timer);
  }, [feedbackDue, jobId, emailPopupOpen, showPasswordModal]);

  const closeFeedback = useCallback(() => setFeedbackOpen(false), []);

  // Out of anonymous free pages: send to signup when they click to upload (not on page load).
  // The server's 401 trial-limit response in handleUpload covers stale usage.
  const trialExhausted = !isLoggedIn && usage?.authenticated === false && usage?.trial_remaining === 0;
  const goToSignup = useCallback(
    (notice = TRIAL_LIMIT_NOTICE) =>
      navigate("/signup", {
        state: {
          from: { pathname: "/scanner" },
          notice: typeof notice === "string" ? notice : TRIAL_LIMIT_NOTICE,
          reason: "trial-exhausted",
        },
      }),
    [navigate]
  );
  // Rows the latest chat answer returned, as indices into `transactions`, highlighted in the table.
  const [answerHighlight, setAnswerHighlight] = useState(null); // { indices: Set<number>, question }
  const handleAnswerRows = useCallback(
    (rows, question) => {
      setAnswerHighlight(rows.length ? { indices: matchRowIndices(transactions, rows), question } : null);
    },
    [transactions],
  );
  useEffect(() => setAnswerHighlight(null), [jobId]);

  // A reconciliation hint's "Show row": clear filters, highlight the rows, scroll to the first.
  const handleJumpToRows = useCallback((indices) => {
    setCategoryFilter(null);
    setAnswerHighlight({ indices: new Set(indices), note: "The reconciliation check points here" });
    requestAnimationFrame(() => {
      document
        .querySelector(`[data-row-index="${Math.min(...indices)}"]`)
        ?.scrollIntoView({ behavior: "smooth", block: "center" });
    });
  }, []);

  // Guest wants chat: keep their statement in this browser so it reopens after signup
  // (login returns to /scanner?handoff=1; the dashboard offers it after email confirmation).
  const lastFileRef = useRef(null);
  const goToSignupForChat = useCallback(async () => {
    const kept = lastFileRef.current ? await handOffFile(lastFileRef.current) : false;
    navigate("/signup", {
      state: {
        from: { pathname: "/scanner", search: kept ? "?handoff=1" : "" },
        notice: CHAT_NOTICE,
        reason: "chat",
      },
    });
  }, [navigate]);
  const goToSignupForFileSize = useCallback(
    () =>
      navigate("/signup", {
        state: { from: { pathname: "/scanner" }, notice: FILE_SIZE_NOTICE, reason: "file-too-large" },
      }),
    [navigate]
  );

  // Upload limit for this user's tier (20 MB guest / 30 MB free account / 50 MB subscriber).
  const fileLimit = maxFileBytes(usage, isLoggedIn);
  const showFileTooLarge = (sizeBytes, maxBytes = fileLimit) => {
    const { message, upgrade } = fileTooLarge(sizeBytes, maxBytes);
    setOutOfCredits(false);
    setError(message);
    setTooLargeUpgrade(upgrade);
    trackEvent("file_too_large", {
      size_mb: Math.round(sizeBytes / MB),
      limit_mb: Math.round(maxBytes / MB),
      logged_in: isLoggedIn,
    });
  };

  // Load existing job when opening from dashboard (e.g. /scanner/:jobId)
  useEffect(() => {
    if (!routeJobId) return;
    setTooLargeUpgrade(null);
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
          setReconciliation(data.reconciliation ?? null);
          setReconciliationStale(false);
          setDataStatus(data.data_status ?? null);
          setTrialCsvContent(null);
        } else {
          setError("Job not found");
        }
      })
      .catch((e) => setError(e.message || "Failed to load job"))
      .finally(() => setLoadingJob(false));
  }, [routeJobId, isLoggedIn]);

  const handleUpload = async (file, password) => {
    lastFileRef.current = file;
    // With a password the modal stays up ("Unlocking…") until the server accepts it,
    // then closes and the page loader takes over. Without one, show the loader right away.
    const viaPassword = password != null;
    // Reject oversized files before uploading. Skipped while auth is still loading (the tier
    // isn't known yet); the server enforces the same limit either way.
    if (!authLoading && file.size > fileLimit) {
      showFileTooLarge(file.size);
      return;
    }
    const showLoader = () => {
      setLoading(true);
      setLoadingFile({ name: file.name, size: file.size });
    };
    setError(null);
    setOutOfCredits(false);
    setTooLargeUpgrade(null);
    setDownloadError(null);
    setJobId(null);
    setTransactions([]);
    setSummaryByCategory([]);
    setCurrency(null);
    setReconciliation(null);
    setReconciliationStale(false);
    setDataStatus(null);
    setTrialCsvContent(null);
    setScanProgress({ stage: "uploading" });
    if (!viaPassword) {
      showLoader();
      pushDataLayer({ event: "scan_started", logged_in: isLoggedIn, mode: conversionMode });
    }
    try {
      const data = await runScan(
        file,
        { incognitoMode, conversionMode, password },
        {
          onStarted: () => {
            if (viaPassword) {
              handlePasswordModalClose();
              showLoader();
            }
          },
          onProgress: setScanProgress,
        },
      );
      scrollToResultsRef.current = true;
      setJobId(data.job_id);
      setTransactions(data.transactions || []);
      setSummaryByCategory(data.summary_by_category || []);
      setCurrency(data.currency ?? null);
      setReconciliation(data.reconciliation ?? null);
      setReconciliationStale(false);
      setDataStatus(null);
      setTrialCsvContent(data.csv_content ?? null);
      applyUsage(data);
      refreshUsage();
      trackEvent("scan_completed", { rows: (data.transactions || []).length, logged_in: isLoggedIn });
      // Anonymous free scan = top of the scan-first funnel for LinkedIn ads.
      if (!isLoggedIn) trackLinkedInConversion(LINKEDIN_TRIAL_SCAN_CONVERSION_ID, data.job_id);
      if (noteScanForFeedback()) setFeedbackDue(true);
    } catch (e) {
      if (e.isPdfPasswordRequired) {
        setPendingPasswordFile(file);
        setShowPasswordModal(true);
        setPasswordError(null);
        setPasswordInput("");
        return;
      }
      if (e.isPdfPasswordIncorrect && viaPassword) {
        setPasswordError("Incorrect password. Please try again.");
        return;
      }
      // Any other failure is shown on the page, not in the password dialog.
      if (viaPassword) handlePasswordModalClose();
      if (e.fileTooLarge) {
        showFileTooLarge(e.fileTooLarge.size_bytes, e.fileTooLarge.max_bytes);
        return;
      }
      if (e.isTrialLimit && !isLoggedIn) {
        goToSignup(e.freePagesExceeded ? e.message : TRIAL_LIMIT_NOTICE);
        return;
      }
      if (e.insufficientCredits) {
        setOutOfCredits(true);
        setError(e.message || "You're out of pages. Subscribe or buy a page pack to keep scanning.");
      } else {
        setError(e.message || "Upload failed");
      }
    } finally {
      setLoading(false);
      setLoadingFile(null);
      setScanProgress(null);
      setCheckingPassword(false);
    }
  };

  const handlePasswordSubmit = (password) => {
    if (!pendingPasswordFile) return;
    setPasswordError(null);
    setCheckingPassword(true);
    handleUpload(pendingPasswordFile, password);
  };

  const handlePasswordModalClose = () => {
    setShowPasswordModal(false);
    setPendingPasswordFile(null);
    setPasswordError(null);
    setPasswordInput("");
  };

  // Entry points from the marketing site:
  //  ?handoff=1 — a file dropped on the landing page's upload box (stored in IndexedDB); start scanning it.
  //  ?sample=1  — show the built-in sample statement's results (no upload, no trial used).
  const entryHandled = useRef(false);
  useEffect(() => {
    // Wait for auth so a signed-in user's handed-off file is scanned on their account, not as a guest.
    if (entryHandled.current || routeJobId || authLoading) return;
    const handoff = searchParams.get("handoff") === "1";
    const sample = searchParams.get("sample") === "1";
    if (!handoff && !sample) return;
    entryHandled.current = true;
    setSearchParams({}, { replace: true });
    if (sample) {
      loadSample();
      return;
    }
    takeHandedOffFile().then((file) => {
      if (file) handleUpload(file);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authLoading]);

  const loadSample = () => {
    const rows = sampleStatement.transactions;
    setError(null);
    setTooLargeUpgrade(null);
    setJobId(SAMPLE_JOB_ID);
    setTransactions(rows);
    setSummaryByCategory(computeSummaryByCategory(rows));
    setCurrency(sampleStatement.currency);
    setReconciliation(sampleReconciliation());
    setReconciliationStale(false);
    setDataStatus(null);
    setTrialCsvContent(transactionsToCsvBrowser(rows));
    pushDataLayer({ event: "sample_view", where: "scanner" });
  };

  const hasResults = !!jobId;
  // Fall back to "All" if the selected category no longer exists (e.g. after an edit).
  const activeCategoryFilter =
    categoryFilter &&
    (isDirectionFilter(categoryFilter) || summaryByCategory.some((s) => s.category === categoryFilter))
      ? categoryFilter
      : null;

  // Results render below the upload card; bring the sample into view so it's not missed on phones.
  const sampleBannerRef = useRef(null);
  useEffect(() => {
    if (isSample) sampleBannerRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [isSample]);

  // Same for a fresh scan's results, which otherwise sit under the dropzone (easy to miss,
  // especially after a landing-page handoff where the visitor never touched this page).
  const resultsRef = useRef(null);
  const scrollToResultsRef = useRef(false);
  useEffect(() => {
    if (!jobId || !scrollToResultsRef.current) return;
    scrollToResultsRef.current = false;
    resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [jobId]);

  // "Upload new statement" on the results view: opens a file picker without scrolling back to the dropzone.
  const newUploadInputRef = useRef(null);
  const handleNewUploadClick = () => {
    if (trialExhausted) {
      goToSignup();
      return;
    }
    newUploadInputRef.current?.click();
  };
  const handleNewUploadChange = (e) => {
    const file = e.target?.files?.[0];
    e.target.value = "";
    if (!file || file.type !== "application/pdf") return;
    handleUpload(file);
  };

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
    if (!(jobId && !isSample && isLoggedIn && !dataStatus)) setReconciliationStale(true);

    // Persist changes for stored jobs (non-incognito / not purged)
    if (jobId && !isSample && isLoggedIn && !dataStatus) {
      try {
        const updated = await updateJobTransactions(jobId, nextTransactions);
        setReconciliation(updated.reconciliation ?? null);
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
    if (!(jobId && !isSample && isLoggedIn && !dataStatus)) setReconciliationStale(true);

    if (jobId && !isSample && isLoggedIn && !dataStatus) {
      try {
        const updated = await updateJobTransactions(jobId, nextTransactions);
        setReconciliation(updated.reconciliation ?? null);
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
        {isGuest ? (
          <div className="scanner-head scanner-head--guest">
            <h1 className="scanner-title">Turn your bank statement PDF into a spreadsheet</h1>
            <p className="scanner-subtitle">
              Drop the PDF below and get every transaction back as a clean, categorized table in seconds.
            </p>
            <ul className="scanner-trust" aria-label="Why it's easy">
              <li>Free, no signup needed</li>
              <li>Encrypted upload</li>
              <li>Download Excel or CSV</li>
            </ul>
          </div>
        ) : (
          <div className="scanner-head">
            <h1 className="scanner-title">Process statement</h1>
            <p className="scanner-subtitle">Upload a PDF or open a past job from your dashboard.</p>
          </div>
        )}

        <div className="scanner-main">
        {/* While a scan runs, the loader takes the upload card's place. Otherwise a file handed
            off from the landing page scans below the fold under an idle-looking dropzone. */}
        {!loading && (
        <div className="scanner-upload-card">
          {isGuest && trialExhausted && (
            <p className="scanner-trial-note" role="status">
              The {FREE_ANON_PAGES} free pages for your network have been used.{" "}
              <button type="button" className="scanner-alert-link" onClick={goToSignup}>
                Create a free account
              </button>{" "}
              to get {FREE_SIGNUP_PAGES} free pages this month, or view the sample below.
            </p>
          )}
          {isGuest && (
            <FileUpload
              onUpload={handleUpload}
              disabled={loading}
              blocked={trialExhausted}
              onBlocked={goToSignup}
              maxBytes={fileLimit}
              onTooLarge={showFileTooLarge}
            />
          )}
          {isGuest && !loading && (
            <div className="scanner-sample-cta">
              <span>No PDF handy?</span>
              <button type="button" className="scanner-sample-btn" onClick={loadSample}>
                See a sample result
              </button>
            </div>
          )}
          <details className="scanner-advanced" open={!isGuest || undefined}>
          <summary className="scanner-advanced-summary">Advanced options</summary>
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
              <option value="accurate">Accurate — best for complex layouts ({ACCURATE_MULTIPLIER} pages per PDF page)</option>
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
          </details>
          {!isGuest && (
            <FileUpload
              onUpload={handleUpload}
              disabled={loading}
              blocked={trialExhausted}
              onBlocked={goToSignup}
              maxBytes={fileLimit}
              onTooLarge={showFileTooLarge}
            />
          )}
        </div>
        )}

        {loading && (
          <Loader
            fileName={loadingFile?.name}
            fileSize={loadingFile?.size}
            progress={scanProgress}
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
                {tooLargeUpgrade === "signup" && (
                  <>
                    {" "}
                    <button type="button" className="scanner-alert-link" onClick={goToSignupForFileSize}>
                      Create a free account
                    </button>
                  </>
                )}
                {tooLargeUpgrade === "subscribe" && (
                  <>
                    {" "}
                    <button type="button" className="scanner-alert-link" onClick={() => navigate("/settings")}>
                      Subscribe
                    </button>
                  </>
                )}
                {outOfCredits && (
                  <>
                    {" "}
                    <button type="button" className="scanner-alert-link" onClick={() => navigate("/settings#billing")}>
                      Get more pages
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

        {isSample && (
          <div className="scanner-sample-banner" role="status" ref={sampleBannerRef}>
            <div>
              <strong>This is a sample statement.</strong>{" "}
              {sampleStatement.bank} is fictional. Opening balance ${sampleStatement.opening.toLocaleString("en-US", { minimumFractionDigits: 2 })}{" "}
              + credits − debits = closing ${sampleStatement.closing.toLocaleString("en-US", { minimumFractionDigits: 2 })}, matching the statement.{" "}
              <a href="/samples/sample-bank-statement.pdf" target="_blank" rel="noopener">View the original PDF</a>
            </div>
            <span className="scanner-sample-banner-cta">Upload your own statement above to try it for real.</span>
          </div>
        )}

        {hasResults && (
          <>
            <div className="scanner-results" ref={resultsRef}>
              <div className="scanner-results-actions">
                <button
                  type="button"
                  className="scanner-new-upload-btn"
                  onClick={handleNewUploadClick}
                  disabled={loading}
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                    <polyline points="17 8 12 3 7 8" />
                    <line x1="12" y1="3" x2="12" y2="15" />
                  </svg>
                  Upload new statement
                </button>
                <input
                  ref={newUploadInputRef}
                  type="file"
                  accept="application/pdf"
                  onChange={handleNewUploadChange}
                  hidden
                />
                {canEmailSpreadsheet && !emailPopupOpen && (
                  <button type="button" className="email-sheet-reopen" onClick={() => setEmailPopupOpen(true)}>
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                      <rect x="3" y="5" width="18" height="14" rx="2" />
                      <path d="m3.5 6.5 8.5 6 8.5-6" />
                    </svg>
                    Email me this spreadsheet
                  </button>
                )}
              </div>
              <div className="scanner-results-tables">
                <ReconciliationPanel
                  reconciliation={reconciliation}
                  currency={currency}
                  transactions={transactions}
                  onJumpToRow={handleJumpToRows}
                  stale={reconciliationStale}
                  jobId={jobId}
                />
                <SummaryTable
                  summaryByCategory={summaryByCategory}
                  currency={currency}
                  activeCategory={activeCategoryFilter}
                  onSelectCategory={setCategoryFilter}
                  transactions={transactions}
                  onDownloadError={setDownloadError}
                />
                <ResultsTable
                  transactions={transactions}
                  categoryFilter={activeCategoryFilter}
                  onClearCategoryFilter={() => setCategoryFilter(null)}
                  jobId={jobId}
                  onDownloadError={setDownloadError}
                  onTransactionChange={handleTransactionChange}
                  onSaveTransaction={handleSaveTransaction}
                  highlighted={answerHighlight?.indices}
                  highlightQuestion={answerHighlight?.question}
                  highlightNote={answerHighlight?.note}
                  // Edited trial rows no longer match the check, so don't export a stale one.
                  reconciliation={reconciliationStale ? null : reconciliation}
                  onClearHighlight={() => setAnswerHighlight(null)}
                />
              </div>
            </div>

            {!isSample && <div className="scanner-fab-wrap">
              <button
                type="button"
                className="scanner-fab"
                onClick={() => setChatOpen(true)}
                aria-label="Ask your statement"
                title="Ask your statement"
              >
                <span className="scanner-fab-icon" aria-hidden>
                  <ChatIcon />
                </span>
                <span className="scanner-fab-tooltip">
                  <span className="scanner-fab-tooltip-text-full">Ask your statement – find, total and export transactions</span>
                  <span className="scanner-fab-tooltip-text-mobile">Ask your statement</span>
                </span>
              </button>
            </div>}

            {chatOpen && !isSample && (
              <div className="scanner-chat-drawer-backdrop" onClick={() => setChatOpen(false)} aria-hidden />
            )}
            {!isSample && <div className={`scanner-chat-drawer ${chatOpen ? "scanner-chat-drawer--open" : ""}`}>
              <div className="scanner-chat-drawer-inner">
                <div className="scanner-chat-drawer-header">
                  <div>
                    <h2 className="scanner-chat-drawer-title">Ask your statement</h2>
                    <p className="scanner-chat-drawer-sub">Find, total and export any transactions</p>
                  </div>
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
                  onRequireLogin={goToSignupForChat}
                  onAnswerRows={handleAnswerRows}
                  hideHeading
                />
              </div>
            </div>}
          </>
        )}
        </div>
      </div>

      {emailPopupOpen && canEmailSpreadsheet && (
        <EmailSpreadsheet
          key={jobId}
          jobId={jobId}
          transactions={transactions}
          reconciliation={reconciliationStale ? null : reconciliation}
          onClose={() => setEmailPopupOpen(false)}
        />
      )}

      {feedbackOpen && <FeedbackPrompt jobId={jobId} isLoggedIn={isLoggedIn} onClose={closeFeedback} />}

      {showPasswordModal && (
        <div className="scanner-password-modal-backdrop" onClick={checkingPassword ? undefined : handlePasswordModalClose} aria-hidden />
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
            <PasswordInput
              id="pdf-password-input"
              className="scanner-password-modal-input"
              value={passwordInput}
              onChange={(e) => setPasswordInput(e.target.value)}
              placeholder="Enter PDF password"
              autoComplete="current-password"
              disabled={checkingPassword}
              autoFocus
            />
            <div className="scanner-password-modal-actions">
              <button type="button" className="scanner-password-modal-btn secondary" onClick={handlePasswordModalClose} disabled={checkingPassword}>
                Cancel
              </button>
              <button type="submit" className="scanner-password-modal-btn primary" disabled={checkingPassword || !passwordInput.trim()}>
                {checkingPassword ? "Unlocking…" : "Unlock"}
              </button>
            </div>
          </form>
        </div>
      )}
    </AppLayout>
  );
}
