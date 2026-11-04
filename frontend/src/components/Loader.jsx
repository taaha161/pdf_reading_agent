import "./Loader.css";

const LARGE_FILE_THRESHOLD_MB = 2;

// Mirrors the backend's scan stages (services/scan_jobs.py STAGES), plus the upload.
const STEPS = [
  { stage: "uploading", label: "Uploading PDF…" },
  { stage: "reading", label: "Reading document (text or OCR)…" },
  { stage: "extracting", label: "Extracting & categorizing transactions…" },
  { stage: "finalizing", label: "Preparing your results…" },
];

function formatSize(bytes) {
  if (bytes == null || bytes === 0) return null;
  const mb = bytes / (1024 * 1024);
  if (mb >= 1) return `${mb.toFixed(1)} MB`;
  return `${(bytes / 1024).toFixed(0)} KB`;
}

export default function Loader({ fileName, fileSize, progress }) {
  const found = STEPS.findIndex((s) => s.stage === progress?.stage);
  const stepIndex = found === -1 ? 0 : found;
  const isLarge = fileSize != null && fileSize > LARGE_FILE_THRESHOLD_MB * 1024 * 1024;
  const sizeStr = formatSize(fileSize);
  const partDetail =
    STEPS[stepIndex].stage === "extracting" && progress?.chunks > 1
      ? `Part ${progress.chunk} of ${progress.chunks}`
      : null;

  return (
    <div className="loader-wrap" role="status" aria-label="Processing PDF">
      <div className="loader-spinner" />
      <p className="loader-message" aria-live="polite">{STEPS[stepIndex].label}</p>
      {partDetail && <p className="loader-detail">{partDetail}</p>}
      <ul className="loader-steps" aria-hidden="true">
        {STEPS.map(({ stage, label }, i) => (
          <li
            key={stage}
            className={i === stepIndex ? "active" : i < stepIndex ? "done" : ""}
          >
            {label}
          </li>
        ))}
      </ul>
      {isLarge && (
        <p className="loader-hint">
          Large file ({sizeStr}) — this may take a minute or two.
        </p>
      )}
      {fileName && (
        <p className="loader-filename" title={fileName} data-clarity-mask="true">
          {fileName.length > 40 ? fileName.slice(0, 37) + "…" : fileName}
        </p>
      )}
    </div>
  );
}
