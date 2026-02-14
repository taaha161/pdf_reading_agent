const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

const UPLOAD_TIMEOUT_MS = 5 * 60 * 1000; // 5 minutes for LLM processing

function getErrorMessage(err) {
  if (err instanceof TypeError && err.message === "Failed to fetch") {
    return `Cannot reach the backend at ${API_BASE}. Is it running? Check the URL and CORS.`;
  }
  return err.message || "Request failed";
}

export async function processPdf(file) {
  const form = new FormData();
  form.append("file", file);
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), UPLOAD_TIMEOUT_MS);
  let res;
  try {
    res = await fetch(`${API_BASE}/api/process-pdf`, {
      method: "POST",
      body: form,
      signal: controller.signal,
    });
  } catch (e) {
    clearTimeout(timeoutId);
    throw new Error(getErrorMessage(e));
  }
  clearTimeout(timeoutId);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    const msg = Array.isArray(err.detail) ? err.detail.map((d) => d.msg || d).join(", ") : (err.detail || res.statusText);
    throw new Error(msg);
  }
  return res.json();
}

export async function downloadCsv(jobId) {
  const res = await fetch(`${API_BASE}/api/jobs/${jobId}/csv`);
  if (!res.ok) throw new Error("Failed to download CSV");
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "statement.csv";
  a.click();
  URL.revokeObjectURL(url);
}

export async function sendChatMessage(jobId, message) {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ job_id: jobId, message }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    const msg = Array.isArray(err.detail) ? err.detail.map((d) => d.msg || d).join(", ") : (err.detail || res.statusText);
    throw new Error(msg);
  }
  const data = await res.json();
  return data.reply;
}
