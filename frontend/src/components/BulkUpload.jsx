import { useCallback, useEffect, useRef, useState } from "react";
import { exportStatements, runScan } from "../api/client";
import { formatMB } from "../lib/fileSize";
import { trackEvent } from "../lib/analytics";
import { signedInPagesExceeded } from "../lib/pageLimit";
import { useUsage } from "../contexts/UsageContext";
import PasswordInput from "./PasswordInput";
import "./BulkUpload.css";

/** Scans run two at a time: quick for a stack of PDFs, gentle on the per-minute upload limit. */
const CONCURRENCY = 2;
export const MAX_BULK_FILES = 50; // matches the backend's combined-download limit
const RATE_LIMIT_WAIT_MS = 20_000;
const RATE_LIMIT_RETRIES = 3;

const STAGE_LABELS = {
  waiting: "Waiting for a free slot…",
  uploading: "Uploading…",
  reading: "Reading…",
  extracting: "Extracting transactions…",
  finalizing: "Finishing…",
};

const RECONCILE_LABELS = { reconciled: "Totals match", mismatch: "Check totals" };

let nextId = 0;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function makeItems(files, maxBytes) {
  return files.map((file) => ({
    id: ++nextId,
    file,
    status: file.size > maxBytes ? "error" : "queued",
    error: file.size > maxBytes ? `Larger than your ${formatMB(maxBytes)} limit` : null,
    progress: null,
    password: null,
    result: null,
  }));
}

function stageLabel(progress) {
  const label = STAGE_LABELS[progress?.stage] || "Scanning…";
  return progress?.stage === "extracting" && progress.chunks > 1 ? `${label} ${progress.chunk}/${progress.chunks}` : label;
}

/**
 * Bulk upload: scans a list of PDFs one after another (CONCURRENCY at a time) with the same
 * /api/scans flow as a single upload, so each statement is billed, stored and listed on the
 * dashboard as its own job. Shows per-file progress, asks for passwords inline, stops when
 * pages run out, and offers one combined Excel/CSV download.
 *
 * - options: { incognitoMode, conversionMode } used for every file in the batch
 * - onScanned(data): a file finished (data = the scan result; update usage etc.)
 * - onOpen(data, fileName): show one statement's full results on the page
 * - onClose(): leave bulk mode
 */
export default function BulkUpload({ files, options, maxBytes, onScanned, onOpen, onClose, openJobId }) {
  const [items, setItems] = useState(() => makeItems(files.slice(0, MAX_BULK_FILES), maxBytes));
  const [dropped] = useState(Math.max(0, files.length - MAX_BULK_FILES));
  const [outOfPages, setOutOfPages] = useState(null); // { pages_required, pages_remaining } from the 402
  const { usage } = useUsage();
  const [downloading, setDownloading] = useState(null);
  const [downloadError, setDownloadError] = useState(null);
  const started = useRef(new Set());
  const addInputRef = useRef(null);
  const trackedDone = useRef(false);

  const update = useCallback((id, patch) => {
    setItems((prev) => prev.map((i) => (i.id === id ? { ...i, ...patch } : i)));
  }, []);

  const scan = useCallback(
    async (item) => {
      for (let attempt = 0; ; attempt++) {
        try {
          const data = await runScan(
            item.file,
            { ...options, password: item.password },
            { onProgress: (progress) => update(item.id, { progress }) },
          );
          update(item.id, { status: "done", result: data, error: null, progress: null });
          onScanned?.(data);
          return;
        } catch (e) {
          if (e.rateLimited && attempt < RATE_LIMIT_RETRIES) {
            update(item.id, { progress: { stage: "waiting" } });
            await sleep(RATE_LIMIT_WAIT_MS);
            continue;
          }
          if (e.isPdfPasswordRequired || e.isPdfPasswordIncorrect) {
            update(item.id, {
              status: "password",
              progress: null,
              error: e.isPdfPasswordIncorrect ? "Incorrect password. Try again." : null,
            });
          } else if (e.insufficientCredits) {
            setOutOfPages(e.insufficientCredits);
            update(item.id, { status: "queued", progress: null, error: null });
            started.current.delete(item.id); // retried on Resume
          } else {
            update(item.id, { status: "error", progress: null, error: e.message || "Scan failed" });
          }
          return;
        }
      }
    },
    [options, update, onScanned],
  );

  // Start queued files while there's a free slot (and pages left).
  useEffect(() => {
    if (outOfPages) return;
    const running = items.filter((i) => i.status === "scanning").length;
    const next = items
      .filter((i) => i.status === "queued" && !started.current.has(i.id))
      .slice(0, Math.max(0, CONCURRENCY - running));
    if (!next.length) return;
    next.forEach((i) => started.current.add(i.id));
    setItems((prev) => prev.map((i) => (next.some((n) => n.id === i.id) ? { ...i, status: "scanning", progress: { stage: "uploading" } } : i)));
    next.forEach(scan);
  }, [items, outOfPages, scan]);

  const done = items.filter((i) => i.status === "done");
  const active = items.some((i) => i.status === "scanning" || (i.status === "queued" && !outOfPages));
  const failed = items.filter((i) => i.status === "error").length;
  const needPassword = items.filter((i) => i.status === "password").length;
  const finished = items.length - items.filter((i) => i.status === "queued" || i.status === "scanning").length;
  const rows = done.reduce((n, i) => n + (i.result?.transactions?.length || 0), 0);

  useEffect(() => {
    if (active || trackedDone.current || !done.length) return;
    trackedDone.current = true;
    trackEvent("bulk_scan_completed", { files: items.length, done: done.length, failed });
  }, [active, done.length, items.length, failed]);

  const retry = (id) => {
    started.current.delete(id);
    update(id, { status: "queued", error: null });
  };

  const unlock = (id, password) => {
    if (!password.trim()) return;
    started.current.delete(id);
    update(id, { status: "queued", password: password.trim(), error: null });
  };

  const skip = (id) => update(id, { status: "error", error: "Skipped (password protected)" });

  const resume = () => setOutOfPages(false);

  const addFiles = (e) => {
    const pdfs = Array.from(e.target.files || []).filter((f) => f.type === "application/pdf");
    e.target.value = "";
    const room = MAX_BULK_FILES - items.length;
    if (pdfs.length && room > 0) setItems((prev) => [...prev, ...makeItems(pdfs.slice(0, room), maxBytes)]);
  };

  const download = async (format) => {
    setDownloading(format);
    setDownloadError(null);
    try {
      await exportStatements(
        done.map((i) => ({ name: i.file.name, transactions: i.result.transactions || [] })),
        { format, currency: done.find((i) => i.result?.currency)?.result.currency },
      );
      trackEvent("bulk_download", { format, files: done.length });
    } catch (e) {
      setDownloadError(e.message || "Download failed");
    } finally {
      setDownloading(null);
    }
  };

  return (
    <section className="bulk" aria-labelledby="bulk-title">
      <header className="bulk-head">
        <div>
          <h2 id="bulk-title" className="bulk-title">
            Bulk upload · {items.length} statement{items.length === 1 ? "" : "s"}
          </h2>
          <p className="bulk-sub" role="status">
            {active
              ? `Scanning… ${finished} of ${items.length} finished`
              : `${done.length} converted · ${rows.toLocaleString()} transactions`}
            {failed > 0 && ` · ${failed} failed`}
            {needPassword > 0 && ` · ${needPassword} need a password`}
          </p>
        </div>
        <div className="bulk-actions">
          <button type="button" className="bulk-btn bulk-btn--primary" onClick={() => download("xlsx")} disabled={!done.length || !!downloading}>
            {downloading === "xlsx" ? "Preparing…" : "Download all (Excel)"}
          </button>
          <button type="button" className="bulk-btn" onClick={() => download("csv")} disabled={!done.length || !!downloading}>
            {downloading === "csv" ? "Preparing…" : "CSV"}
          </button>
          <button type="button" className="bulk-btn" onClick={() => download("quickbooks")} disabled={!done.length || !!downloading} title="Import-ready CSV for QuickBooks Online">
            {downloading === "quickbooks" ? "Preparing…" : "QuickBooks"}
          </button>
          <button type="button" className="bulk-btn" onClick={() => download("xero")} disabled={!done.length || !!downloading} title="Import-ready CSV for Xero">
            {downloading === "xero" ? "Preparing…" : "Xero"}
          </button>
        </div>
      </header>

      <div className="bulk-bar" aria-hidden>
        <span style={{ width: `${items.length ? (finished / items.length) * 100 : 0}%` }} />
      </div>

      {dropped > 0 && (
        <p className="bulk-note">Only the first {MAX_BULK_FILES} files were added. Upload the other {dropped} in a second batch.</p>
      )}
      {outOfPages && (() => {
        const over = signedInPagesExceeded(outOfPages, usage?.subscription_active);
        return (
          <p className="bulk-note bulk-note--warn" role="alert">
            {over.message} The remaining statements are paused.{" "}
            <a href="/settings#billing" target="_blank" rel="noopener">{over.cta}</a>, then{" "}
            <button type="button" className="bulk-link" onClick={resume}>resume</button>.
          </p>
        );
      })()}
      {downloadError && <p className="bulk-note bulk-note--warn" role="alert">{downloadError}</p>}

      <ul className="bulk-list">
        {items.map((item) => (
          <li key={item.id} className={`bulk-item bulk-item--${item.status} ${item.result?.job_id && item.result.job_id === openJobId ? "bulk-item--open" : ""}`}>
            <span className="bulk-dot" aria-hidden />
            <div className="bulk-file">
              <span className="bulk-name" title={item.file.name}>{item.file.name}</span>
              <span className="bulk-meta">
                {item.status === "queued" && (outOfPages ? "Paused" : "Queued")}
                {item.status === "scanning" && stageLabel(item.progress)}
                {item.status === "done" && (
                  <>
                    {(item.result.transactions?.length || 0).toLocaleString()} transactions
                    {RECONCILE_LABELS[item.result.reconciliation?.status] && (
                      <span className={`bulk-tag bulk-tag--${item.result.reconciliation.status}`}>
                        {RECONCILE_LABELS[item.result.reconciliation.status]}
                      </span>
                    )}
                  </>
                )}
                {item.status === "error" && <span className="bulk-error">{item.error}</span>}
                {item.status === "password" && (item.error ? <span className="bulk-error">{item.error}</span> : "Password protected")}
              </span>
            </div>
            <div className="bulk-item-actions">
              {item.status === "done" && (
                <button type="button" className="bulk-btn bulk-btn--small" onClick={() => onOpen(item.result, item.file.name)}>
                  {item.result.job_id === openJobId ? "Showing" : "View"}
                </button>
              )}
              {item.status === "error" && item.file.size <= maxBytes && (
                <button type="button" className="bulk-btn bulk-btn--small" onClick={() => retry(item.id)}>Retry</button>
              )}
              {item.status === "password" && <PasswordRow onUnlock={(p) => unlock(item.id, p)} onSkip={() => skip(item.id)} />}
            </div>
          </li>
        ))}
      </ul>

      <footer className="bulk-foot">
        <button
          type="button"
          className="bulk-btn"
          onClick={() => addInputRef.current?.click()}
          disabled={items.length >= MAX_BULK_FILES}
        >
          Add more PDFs
        </button>
        <input ref={addInputRef} type="file" accept="application/pdf" multiple hidden onChange={addFiles} />
        <button type="button" className="bulk-link" onClick={onClose} disabled={active}>
          {active ? "Scanning… keep this tab open" : "Start a new upload"}
        </button>
      </footer>
    </section>
  );
}

function PasswordRow({ onUnlock, onSkip }) {
  const [value, setValue] = useState("");
  return (
    <form
      className="bulk-password"
      onSubmit={(e) => {
        e.preventDefault();
        onUnlock(value);
      }}
    >
      <PasswordInput
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="PDF password"
        autoComplete="off"
        aria-label="PDF password"
      />
      <button type="submit" className="bulk-btn bulk-btn--small bulk-btn--primary" disabled={!value.trim()}>Unlock</button>
      <button type="button" className="bulk-link" onClick={onSkip}>Skip</button>
    </form>
  );
}
