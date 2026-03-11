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

export async function processPdf(file, options = {}) {
  const form = new FormData();
  form.append("file", file);
  if (options.incognitoMode) {
    form.append("incognito_mode", "true");
  }
  const mode = options.conversionMode && ["fast", "balanced", "accurate"].includes(options.conversionMode) ? options.conversionMode : "fast";
  form.append("conversion_mode", mode);
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), UPLOAD_TIMEOUT_MS);
  let res;
  try {
    res = await fetch(`${API_BASE}/api/process-pdf`, {
      method: "POST",
      headers: authHeaders(),
      body: form,
      signal: controller.signal,
      credentials: "include",
    });
  } catch (e) {
    clearTimeout(timeoutId);
    const message = getErrorMessage(e);
    throw new Error(message);
  }
  clearTimeout(timeoutId);
  if (!res.ok) {
    if (res.status === 429) {
      throw new Error("Too many requests. Please try again in a minute.");
    }
    if (res.status === 402) {
      const data = await res.json().catch(() => ({}));
      const detail = data.detail && typeof data.detail === "object" ? data.detail : {};
      const e = new Error(detail.detail || "Insufficient credits");
      e.insufficientCredits = {
        code: detail.code || "INSUFFICIENT_CREDITS",
        balance_cents: detail.balance_cents ?? 0,
        required_cents: detail.required_cents ?? 0,
      };
      throw e;
    }
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    const msg = Array.isArray(err.detail) ? err.detail.map((d) => d.msg || d).join(", ") : (err.detail || res.statusText);
    const e = new Error(msg);
    if (res.status === 401 && msg && msg.toLowerCase().includes("trial limit")) {
      e.isTrialLimit = true;
    }
    throw e;
  }
  return res.json();
}

export async function getBillingBalance() {
  const res = await fetch(`${API_BASE}/api/billing/balance`, {
    headers: authHeaders(),
    credentials: "include",
  });
  if (!res.ok) {
    if (res.status === 429) throw new Error("Too many requests. Please try again in a minute.");
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to load billing balance");
  }
  return res.json();
}

export async function createCheckoutSession(mode, email = null) {
  const body = { mode };
  if (email) body.email = email;
  const res = await fetch(`${API_BASE}/api/billing/checkout-session`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
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

export async function downloadCsv(jobId) {
  const res = await fetch(`${API_BASE}/api/jobs/${jobId}/csv`, { headers: authHeaders() });
  if (!res.ok) {
    if (res.status === 429) throw new Error("Too many requests. Please try again in a minute.");
    throw new Error("Failed to download CSV");
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "statement.csv";
  a.click();
  URL.revokeObjectURL(url);
}

export async function downloadMarkdown(jobId) {
  const res = await fetch(`${API_BASE}/api/jobs/${jobId}/markdown`, { headers: authHeaders() });
  if (!res.ok) {
    if (res.status === 429) throw new Error("Too many requests. Please try again in a minute.");
    throw new Error("Failed to download markdown");
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "datalab-extract.md";
  a.click();
  URL.revokeObjectURL(url);
}

export async function sendChatMessage(jobId, message) {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ job_id: jobId, message }),
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
  return data.reply;
}
