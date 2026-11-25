import { getRecaptchaToken } from "../lib/recaptcha";
import { getGaIds } from "../lib/analytics";
import { captureMessage } from "../lib/monitoring";

let API_BASE = "http://localhost:8000";

export function setApiBase(url) {
  API_BASE = url || API_BASE;
}

const UPLOAD_TIMEOUT_MS = 15 * 60 * 1000; // 15 minutes (scanned PDFs + OCR/vision can be slow)

/** Set from AuthProvider so API calls include Bearer token. */
let authGetToken = null;
export function setApiAuthToken(getToken) {
  authGetToken = getToken;
}

function authHeaders(token) {
  const headers = {};
  const t = token !== undefined ? token : (typeof authGetToken === "function" ? authGetToken() : null);
  if (t) headers.Authorization = `Bearer ${t}`;
  return headers;
}

function getErrorMessage(err) {
  if (err instanceof TypeError && err.message === "Failed to fetch") {
    return `Cannot reach the backend at ${API_BASE}. Is it running? Check the URL and CORS.`;
  }
  if (err.name === "AbortError") {
    return "Request took too long and was cancelled. Try a smaller PDF or try again.";
  }
  return err.message || "Request failed";
}

/** Build the Error the UI expects from an API error status + FastAPI `detail`. */
function scanError(status, detail, fallback) {
  // 5xx: report from the client too, so proxy/gateway failures the backend never saw show up.
  if (status >= 500) {
    const text = typeof detail === "string" ? detail : detail?.detail || fallback;
    captureMessage(`API error ${status}: ${text}`, { tags: { area: "api", status_code: String(status) } });
  }
  if (status === 429) return new Error("Too many requests. Please try again in a minute.");
  const obj = detail && typeof detail === "object" && !Array.isArray(detail) ? detail : null;
  if (status === 402) {
    const e = new Error(obj?.detail || "Not enough pages left");
    e.insufficientCredits = {
      code: obj?.code || "INSUFFICIENT_CREDITS",
      pages_required: obj?.pages_required ?? 0,
      pages_remaining: obj?.pages_remaining ?? 0,
    };
    return e;
  }
  const msg = Array.isArray(detail) ? detail.map((d) => d.msg || d).join(", ") : obj?.detail || detail || fallback;
  const e = new Error(msg);
  if (status === 403 && obj?.code === "RECAPTCHA_FAILED") e.isRecaptchaFailed = true;
  // Anonymous free pages used up. The string check covers a backend deployed before TRIAL_LIMIT existed.
  if (status === 401 && (obj?.code === "TRIAL_LIMIT" || (typeof msg === "string" && msg.toLowerCase().includes("trial limit")))) {
    e.isTrialLimit = true;
  }
  // Anonymous PDF bigger than the free pages left: sign up to scan it.
  if (status === 401 && obj?.code === "FREE_PAGES_EXCEEDED") {
    e.isTrialLimit = true;
    e.freePagesExceeded = { pages_required: obj.pages_required ?? 0, pages_remaining: obj.pages_remaining ?? 0 };
  }
  if (status === 422 && obj?.code === "PDF_PASSWORD_REQUIRED") e.isPdfPasswordRequired = true;
  if (status === 422 && obj?.code === "PDF_PASSWORD_INCORRECT") e.isPdfPasswordIncorrect = true;
  if (status === 413 && obj?.code === "FILE_TOO_LARGE") {
    e.fileTooLarge = { size_bytes: obj.size_bytes, max_bytes: obj.max_bytes, upgrade: obj.upgrade ?? null };
  }
  return e;
}

async function responseError(res) {
  const body = await res.json().catch(() => ({ detail: res.statusText }));
  return scanError(res.status, body.detail, res.statusText);
}

const SCAN_POLL_INTERVAL_MS = 1500;
const SCAN_POLL_MAX_FAILURES = 5; // consecutive network errors tolerated while polling

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

/**
 * Upload a PDF and start a background scan. Rejects right away on validation,
 * trial/credit and password errors. Resolves with { scan_id, status, stage }.
 */
export async function startScan(file, options = {}) {
  const form = new FormData();
  form.append("file", file);
  if (options.incognitoMode) {
    form.append("incognito_mode", "true");
  }
  if (options.password != null && String(options.password).trim() !== "") {
    form.append("pdf_password", String(options.password).trim());
  }
  const mode = options.conversionMode && ["fast", "balanced", "accurate"].includes(options.conversionMode) ? options.conversionMode : "fast";
  form.append("conversion_mode", mode);
  const recaptchaToken = await getRecaptchaToken("scan_pdf");
  if (recaptchaToken) form.append("recaptcha_token", recaptchaToken);
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), UPLOAD_TIMEOUT_MS);
  let res;
  try {
    res = await fetch(`${API_BASE}/api/scans`, {
      method: "POST",
      headers: authHeaders(),
      body: form,
      signal: controller.signal,
      credentials: "include",
    });
  } catch (e) {
    throw new Error(getErrorMessage(e));
  } finally {
    clearTimeout(timeoutId);
  }
  if (!res.ok) throw await responseError(res);
  return res.json();
}

/** Current state of a scan: { scan_id, status: running|done|error, stage, chunk?, chunks?, result?, error? }. */
export async function getScan(scanId) {
  const res = await fetch(`${API_BASE}/api/scans/${encodeURIComponent(scanId)}`, {
    headers: authHeaders(),
    credentials: "include",
  });
  if (res.status === 404) {
    throw new Error("Processing was interrupted. Please upload the file again.");
  }
  if (!res.ok) {
    const e = await responseError(res);
    e.retryable = res.status === 429 || res.status >= 500;
    throw e;
  }
  return res.json();
}

/**
 * Start a scan and poll until it finishes. Resolves with the scan result
 * (same shape as the old /api/process-pdf response).
 * - onStarted(): called once the upload is accepted (password and other checks passed).
 * - onProgress({ stage, chunk, chunks }): called with each progress update.
 */
export async function runScan(file, options = {}, { onStarted, onProgress } = {}) {
  const started = await startScan(file, options);
  onStarted?.();
  onProgress?.({ stage: started.stage });
  const deadline = Date.now() + UPLOAD_TIMEOUT_MS;
  let failures = 0;
  while (Date.now() < deadline) {
    await sleep(SCAN_POLL_INTERVAL_MS);
    let scan;
    try {
      scan = await getScan(started.scan_id);
      failures = 0;
    } catch (e) {
      const transient = e.retryable || e instanceof TypeError;
      if (!transient || ++failures > SCAN_POLL_MAX_FAILURES) throw e;
      continue;
    }
    if (scan.status === "done") return scan.result;
    if (scan.status === "error") {
      throw scanError(scan.error?.status_code ?? 500, scan.error?.detail, "Processing failed");
    }
    onProgress?.({ stage: scan.stage, chunk: scan.chunk, chunks: scan.chunks });
  }
  throw new Error("Processing is taking too long. Please try again with a smaller PDF.");
}

/** Download a PDF from a public link via the backend (avoids CORS; SSRF-guarded server-side). Returns a File. */
export async function fetchPdfFromUrl(url) {
  let res;
  try {
    res = await fetch(`${API_BASE}/api/fetch-pdf-url`, {
      method: "POST",
      headers: { ...authHeaders(), "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
      credentials: "include",
    });
  } catch (e) {
    throw new Error(getErrorMessage(e));
  }
  if (!res.ok) {
    if (res.status === 429) throw new Error("Too many requests. Please try again in a minute.");
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    if (res.status === 413) throw scanError(413, err.detail, "That PDF is too large");
    const detail = Array.isArray(err.detail) ? "Please enter a valid URL." : err.detail;
    throw new Error(detail || "Couldn't download that PDF");
  }
  const blob = await res.blob();
  const name = res.headers.get("X-Filename") || "statement.pdf";
  return new File([blob], name, { type: "application/pdf" });
}

export async function getBillingBalance(token) {
  const res = await fetch(`${API_BASE}/api/billing/balance`, {
    headers: authHeaders(token),
    credentials: "include",
  });
  if (!res.ok) {
    if (res.status === 429) throw new Error("Too many requests. Please try again in a minute.");
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to load billing balance");
  }
  return res.json();
}

/** Notify backend of a real login (owner email). Best-effort; token passed explicitly. */
export async function notifyLogin(token) {
  try {
    await fetch(`${API_BASE}/api/events/login`, {
      method: "POST",
      headers: authHeaders(token),
      credentials: "include",
    });
  } catch {
    // best-effort: never surface login-notification failures to the user
  }
}

/** Public lookup for the signup form: { valid, discount } for a live code, or null if unknown/unreachable. */
export async function lookupReferral(code) {
  try {
    const res = await fetch(`${API_BASE}/api/referral/${encodeURIComponent(code)}`, { credentials: "include" });
    if (res.status === 404) return { valid: false }; // unknown or inactive code
    return res.ok ? await res.json() : null; // null: couldn't check (network/server)
  } catch {
    return null;
  }
}

/** Bind this new account to an affiliate code. Returns { ok, reason } or null on network/server error. */
export async function claimReferral(code, token) {
  try {
    const res = await fetch(`${API_BASE}/api/referral/claim`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders(token) },
      credentials: "include",
      body: JSON.stringify({ code }),
    });
    return res.ok ? await res.json() : null;
  } catch {
    return null;
  }
}

export async function getUsage() {
  const res = await fetch(`${API_BASE}/api/usage`, {
    headers: authHeaders(),
    credentials: "include",
  });
  if (!res.ok) {
    if (res.status === 429) throw new Error("Too many requests. Please try again in a minute.");
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to load usage");
  }
  return res.json();
}

/** `pack` (topup only): a PAGE_PACKS id (subscribers) or BULK_PACK.id from lib/pricing. */
export async function createCheckoutSession(mode, email = null, offer = null, token = undefined, pack = null) {
  const body = { mode, ...getGaIds() };
  if (pack) body.pack = pack;
  // Global Privacy Control: don't report this purchase to ad platforms.
  if (typeof navigator !== "undefined" && navigator.globalPrivacyControl === true) body.ad_opt_out = true;
  if (email) body.email = email;
  if (offer) body.offer = offer;
  const res = await fetch(`${API_BASE}/api/billing/checkout-session`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders(token) },
    credentials: "include",
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    if (res.status === 429) throw new Error("Too many requests. Please try again in a minute.");
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to create checkout session");
  }
  const data = await res.json();
  return data.url;
}

/** Paid signup: Stripe subscription checkout with no account yet. Returns the Checkout URL. */
export async function startPaidSignup(referralCode = null) {
  const body = { ...getGaIds() };
  if (referralCode) body.referral_code = referralCode;
  if (typeof navigator !== "undefined" && navigator.globalPrivacyControl === true) body.ad_opt_out = true;
  const res = await fetch(`${API_BASE}/api/signup/checkout`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    if (res.status === 429) throw new Error("Too many requests. Please try again in a minute.");
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Couldn't start checkout. Please try again.");
  }
  return (await res.json()).url;
}

/** Paid signup: payment + account state for the /welcome page. */
export async function getPaidSignupSession(sessionId) {
  const res = await fetch(`${API_BASE}/api/signup/session/${encodeURIComponent(sessionId)}`);
  if (!res.ok) return { status: res.status === 429 ? "pending" : "error" };
  return res.json();
}

/** Paid signup: set the first password on the new account. Returns { email }. */
export async function setPaidSignupPassword(sessionId, password) {
  const res = await fetch(`${API_BASE}/api/signup/session/${encodeURIComponent(sessionId)}/password`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password }),
  });
  if (!res.ok) {
    if (res.status === 429) throw new Error("Too many attempts. Please wait a minute and try again.");
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Couldn't save your password. Please try again.");
  }
  return res.json();
}

export async function deleteJobData(jobId) {
  const res = await fetch(`${API_BASE}/api/jobs/${jobId}/data`, {
    method: "DELETE",
    headers: authHeaders(),
    credentials: "include",
  });
  if (!res.ok) {
    if (res.status === 404) throw new Error("Job not found");
    if (res.status === 429) throw new Error("Too many requests. Please try again in a minute.");
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to delete job data");
  }
}

export async function deleteAccount() {
  const res = await fetch(`${API_BASE}/api/account`, {
    method: "DELETE",
    headers: authHeaders(),
    credentials: "include",
  });
  if (!res.ok) {
    if (res.status === 503) {
      throw new Error("Account deletion is not configured. Please contact support.");
    }
    if (res.status === 502) {
      throw new Error("Could not complete account deletion. Please try again or contact support.");
    }
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to delete account");
  }
}

export async function deleteJobsData(jobIds) {
  const res = await fetch(`${API_BASE}/api/jobs/data`, {
    method: "DELETE",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    credentials: "include",
    body: JSON.stringify({ job_ids: jobIds }),
  });
  if (!res.ok) {
    if (res.status === 429) throw new Error("Too many requests. Please try again in a minute.");
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to delete job data");
  }
}

export async function listJobs(token) {
  const res = await fetch(`${API_BASE}/api/jobs`, { headers: authHeaders(token), credentials: "include" });
  if (!res.ok) {
    if (res.status === 429) {
      throw new Error("Too many requests. Please try again in a minute.");
    }
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    const e = new Error(err.detail || "Failed to load jobs");
    e.status = res.status;
    throw e;
  }
  return res.json();
}

export async function getJob(jobId) {
  const res = await fetch(`${API_BASE}/api/jobs/${jobId}`, { headers: authHeaders(), credentials: "include" });
  if (!res.ok) {
    if (res.status === 404) return null;
    if (res.status === 429) {
      throw new Error("Too many requests. Please try again in a minute.");
    }
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    const e = new Error(err.detail || "Failed to load job");
    e.status = res.status;
    throw e;
  }
  return res.json();
}

/** Only the fields the export endpoint accepts (rows may carry UI-only extras). */
function exportRows(transactions) {
  return (transactions || []).map(({ date, description, amount, type, category, balance, group }) => ({
    date, description, amount, type, category, ...(balance ? { balance } : {}), ...(group ? { group } : {}),
  }));
}

/**
 * Download the current transactions as CSV or Excel, with or without the category column.
 * kind "summary" downloads the category totals table (built server-side from the same rows).
 * @param {"csv"|"xlsx"} format
 * @param {"transactions"|"summary"} kind
 * @param {string} [filenameBase] name for the file without extension (defaults to the server's name)
 * @param {boolean} [includeTotals] add count / money in / money out / net under the rows
 */
export async function exportTransactions(
  transactions,
  { format = "csv", includeCategories = true, kind = "transactions", filenameBase, includeTotals = false, reconciliation = null } = {},
) {
  const res = await fetch(`${API_BASE}/api/export`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      transactions: exportRows(transactions),
      format,
      include_categories: includeCategories,
      kind,
      include_totals: includeTotals,
      // Excel only: adds a "Reconciliation" sheet; the rows sheet stays import-ready.
      reconciliation: format === "xlsx" ? reconciliation : null,
    }),
  });
  if (!res.ok) {
    if (res.status === 429) throw new Error("Too many requests. Please try again in a minute.");
    throw new Error("Failed to download file");
  }
  const disposition = res.headers.get("Content-Disposition") || "";
  const filename = (filenameBase && `${filenameBase}.${format}`)
    || /filename="([^"]+)"/.exec(disposition)?.[1]
    || (kind === "summary" ? `statement-summary.${format}` : `statement${includeCategories ? "" : "-uncategorized"}.${format}`);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

/**
 * @param {Array<{role: "user"|"assistant", content: string}>} [history] earlier turns, oldest first
 */
export async function sendChatMessage(jobId, message, history = []) {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ job_id: jobId, message, history }),
  });
  if (!res.ok) {
    if (res.status === 429) {
      throw new Error("Too many requests. Please try again in a minute.");
    }
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    const msg = Array.isArray(err.detail) ? err.detail.map((d) => d.msg || d).join(", ") : (err.detail || res.statusText);
    throw new Error(msg);
  }
  const data = await res.json();
  return { reply: data.reply, transactions: data.transactions || [] };
}

export async function updateJobTransactions(jobId, transactions) {
  const res = await fetch(`${API_BASE}/api/jobs/${jobId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    credentials: "include",
    body: JSON.stringify({ transactions }),
  });
  if (!res.ok) {
    if (res.status === 429) {
      throw new Error("Too many requests. Please try again in a minute.");
    }
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    const msg = Array.isArray(err.detail) ? err.detail.map((d) => d.msg || d).join(", ") : (err.detail || res.statusText);
    throw new Error(msg);
  }
  return res.json();
}

/** Anonymous trial: email the spreadsheet (CSV or Excel) to the user and capture their email. */
export async function emailSpreadsheet(jobId, email, transactions, { format = "xlsx", includeCategories = true, marketingOptIn = false, reconciliation = null } = {}) {
  const res = await fetch(`${API_BASE}/api/email-spreadsheet`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({
      job_id: jobId,
      email,
      transactions: exportRows(transactions),
      format,
      include_categories: includeCategories,
      marketing_opt_in: marketingOptIn,
      reconciliation: format === "xlsx" ? reconciliation : null,
    }),
  });
  if (!res.ok) {
    if (res.status === 422) throw new Error("Please enter a valid email address.");
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    const detail = err.detail || err.error;
    if (res.status === 429 && typeof detail !== "string") {
      throw new Error("Too many requests. Please try again later.");
    }
    throw new Error(typeof detail === "string" ? detail : "Failed to send email");
  }
  return res.json();
}

/** Optional post-scan feedback. Works logged in (Bearer token) or anonymous. */
export async function submitFeedback({ jobId, rating, comment, contactOk = false }) {
  const res = await fetch(`${API_BASE}/api/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    credentials: "include",
    body: JSON.stringify({ job_id: jobId || null, rating: rating || null, comment: comment || null, contact_ok: contactOk }),
  });
  if (!res.ok) {
    if (res.status === 429) throw new Error("Too many requests. Please try again later.");
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(typeof err.detail === "string" ? err.detail : "Couldn't send feedback");
  }
  return res.json();
}

/** Claim the review reward. `proof` = review link or the name it was posted under. One claim per account. */
export async function submitReviewClaim(proof, platform = "g2") {
  const res = await fetch(`${API_BASE}/api/review-claim`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    credentials: "include",
    body: JSON.stringify({ platform, proof }),
  });
  if (!res.ok) {
    if (res.status === 429) throw new Error("Too many requests. Please try again later.");
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(typeof err.detail === "string" ? err.detail : "Couldn't send your claim");
  }
  return res.json();
}
