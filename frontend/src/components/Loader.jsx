import { useEffect, useState } from "react";
import "./Loader.css";

const LARGE_FILE_THRESHOLD_MB = 2;
const STEP_INTERVAL_MS = 4500;

const STEPS = [
  "Uploading PDF…",
  "Reading document (text or OCR)…",
  "Extracting transactions…",
  "Categorizing with AI…",
  "Preparing your results…",
];

function formatSize(bytes) {
  if (bytes == null || bytes === 0) return null;
  const mb = bytes / (1024 * 1024);
  if (mb >= 1) return `${mb.toFixed(1)} MB`;
  return `${(bytes / 1024).toFixed(0)} KB`;
}

export default function Loader({ fileName, fileSize }) {
  const [stepIndex, setStepIndex] = useState(0);
  const isLarge = fileSize != null && fileSize > LARGE_FILE_THRESHOLD_MB * 1024 * 1024;
  const sizeStr = formatSize(fileSize);

  useEffect(() => {
    const id = setInterval(() => {
      setStepIndex((i) => (i + 1) % STEPS.length);
    }, STEP_INTERVAL_MS);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="loader-wrap" role="status" aria-label="Processing PDF">
      <div className="loader-spinner" />
      <p className="loader-message">{STEPS[stepIndex]}</p>
      <ul className="loader-steps" aria-hidden="true">
        {STEPS.map((label, i) => (
          <li
            key={label}
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
        <p className="loader-filename" title={fileName}>
          {fileName.length > 40 ? fileName.slice(0, 37) + "…" : fileName}
        </p>
      )}
    </div>
  );
}
