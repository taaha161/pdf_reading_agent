import { useCallback, useState } from "react";
import { fetchPdfFromUrl } from "../api/client";
import { isGoogleDriveConfigured, pickPdfFromGoogleDrive } from "../lib/googleDrive";
import { formatMB, MAX_FILE_BYTES_ANON } from "../lib/fileSize";
import "./FileUpload.css";

/**
 * `blocked` + `onBlocked`: when the user can't scan (e.g. out of free scans), any attempt to
 * start an upload (click, drop, Drive, URL) calls onBlocked instead of opening a picker.
 * `maxBytes`: the user's upload limit. onUpload checks size for every file; Drive/URL
 * imports that are over the limit before download call `onTooLarge(sizeBytes)` instead.
 */
export default function FileUpload({
  onUpload,
  disabled,
  blocked = false,
  onBlocked,
  maxBytes = MAX_FILE_BYTES_ANON,
  onTooLarge,
}) {
  const [drag, setDrag] = useState(false);
  const [showUrl, setShowUrl] = useState(false);
  const [url, setUrl] = useState("");
  const [importing, setImporting] = useState(null); // "drive" | "url" | null
  const [importError, setImportError] = useState(null);
  const busy = disabled || Boolean(importing);

  const handleFile = useCallback(
    (file) => {
      if (!file || file.type !== "application/pdf") return;
      setImportError(null);
      onUpload(file);
    },
    [onUpload]
  );

  // Returns true (and fires onBlocked) when uploads are blocked.
  const intercept = (e) => {
    if (!blocked) return false;
    e?.preventDefault();
    onBlocked?.();
    return true;
  };

  const onDrop = (e) => {
    e.preventDefault();
    setDrag(false);
    if (busy || intercept(e)) return;
    const file = e.dataTransfer?.files?.[0];
    handleFile(file);
  };

  const onDragOver = (e) => {
    e.preventDefault();
    setDrag(true);
  };

  const onDragLeave = () => setDrag(false);

  const onInputChange = (e) => {
    const file = e.target?.files?.[0];
    handleFile(file);
    e.target.value = "";
  };

  const runImport = async (source, getFile) => {
    setImportError(null);
    setImporting(source);
    let file = null;
    try {
      file = await getFile();
    } catch (err) {
      if (err.fileTooLarge && onTooLarge) onTooLarge(err.fileTooLarge.size_bytes);
      else setImportError(err.message || "Import failed");
    } finally {
      setImporting(null);
    }
    if (file) {
      setUrl("");
      setShowUrl(false);
      handleFile(file);
    }
  };

  const onDriveClick = (e) => !intercept(e) && runImport("drive", () => pickPdfFromGoogleDrive(maxBytes));

  const onUrlSubmit = (e) => {
    e.preventDefault();
    const value = url.trim();
    if (!value) return;
    if (!/^https?:\/\//i.test(value)) {
      setImportError("Enter a full link starting with https://");
      return;
    }
    runImport("url", () => fetchPdfFromUrl(value));
  };

  return (
    <div className="file-upload-wrap">
      <div
        className={`file-upload ${drag ? "drag" : ""} ${busy ? "disabled" : ""}`}
        onDrop={onDrop}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
      >
        <input
          type="file"
          accept="application/pdf"
          onChange={onInputChange}
          disabled={busy}
          id="pdf-input"
        />
        <label htmlFor="pdf-input" className="file-upload-label" onClick={intercept}>
          <span className="file-upload-icon" aria-hidden>
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
              <path d="M12 18v-6" />
              <path d="M9 15l3 3 3-3" />
            </svg>
          </span>
          <span className="file-upload-headline">Drop your bank statement PDF here</span>
          <span className="file-upload-subtext">or click to choose · up to {formatMB(maxBytes)}</span>
        </label>
      </div>

      <div className="file-upload-sources">
        <span className="file-upload-sources-label">Or import from</span>
        <div className="file-upload-sources-buttons">
          {isGoogleDriveConfigured() && (
            <button type="button" className="file-upload-source-btn" onClick={onDriveClick} disabled={busy}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" aria-hidden>
                <path d="M8.5 3h7l6.5 11.5-3.5 6H5.5L2 14.5z" />
                <path d="M8.5 3 15 14.5H2M15.5 3 9 14.5M22 14.5H9l-3.5 6" />
              </svg>
              {importing === "drive" ? "Opening Google Drive…" : "Google Drive"}
            </button>
          )}
          <button
            type="button"
            className={`file-upload-source-btn ${showUrl ? "active" : ""}`}
            onClick={(e) => {
              if (intercept(e)) return;
              setShowUrl((v) => !v);
              setImportError(null);
            }}
            disabled={busy}
            aria-expanded={showUrl}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
              <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
              <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
            </svg>
            From URL
          </button>
        </div>
      </div>

      {showUrl && (
        <form className="file-upload-url" onSubmit={onUrlSubmit}>
          <input
            type="url"
            inputMode="url"
            placeholder="https://… link to a PDF (Google Drive, Dropbox, or direct)"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            disabled={busy}
            aria-label="PDF link"
            autoFocus
          />
          <button type="submit" disabled={busy || !url.trim()}>
            {importing === "url" ? "Downloading…" : "Import"}
          </button>
          <p className="file-upload-url-hint">Share links must be public (&ldquo;Anyone with the link&rdquo;).</p>
        </form>
      )}

      {importError && (
        <p className="file-upload-error" role="alert">
          {importError}
        </p>
      )}
    </div>
  );
}
