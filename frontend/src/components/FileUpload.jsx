import { useCallback, useState } from "react";
import "./FileUpload.css";

export default function FileUpload({ onUpload, disabled }) {
  const [drag, setDrag] = useState(false);

  const handleFile = useCallback(
    (file) => {
      if (!file || file.type !== "application/pdf") return;
      onUpload(file);
    },
    [onUpload]
  );

  const onDrop = (e) => {
    e.preventDefault();
    setDrag(false);
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

  return (
    <div
      className={`file-upload ${drag ? "drag" : ""} ${disabled ? "disabled" : ""}`}
      onDrop={onDrop}
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
    >
      <input
        type="file"
        accept="application/pdf"
        onChange={onInputChange}
        disabled={disabled}
        id="pdf-input"
      />
      <label htmlFor="pdf-input" className="file-upload-label">
        <span className="file-upload-icon" aria-hidden>
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
            <path d="M12 18v-6" />
            <path d="M9 15l3 3 3-3" />
          </svg>
        </span>
        <span className="file-upload-headline">Drop your bank statement PDF here</span>
        <span className="file-upload-subtext">or click to choose</span>
      </label>
    </div>
  );
}
