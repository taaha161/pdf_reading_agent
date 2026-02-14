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
      <label htmlFor="pdf-input">
        Drop a bank statement PDF here, or click to choose
      </label>
    </div>
  );
}
