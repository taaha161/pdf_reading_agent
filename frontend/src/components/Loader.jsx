import "./Loader.css";

const LARGE_FILE_THRESHOLD_MB = 2;

function formatSize(bytes) {
  if (bytes == null || bytes === 0) return null;
  const mb = bytes / (1024 * 1024);
  if (mb >= 1) return `${mb.toFixed(1)} MB`;
  return `${(bytes / 1024).toFixed(0)} KB`;
}

export default function Loader({ fileName, fileSize }) {
  const isLarge = fileSize != null && fileSize > LARGE_FILE_THRESHOLD_MB * 1024 * 1024;
  const sizeStr = formatSize(fileSize);

  return (
    <div className="loader-wrap" role="status" aria-label="Processing PDF">
      <div className="loader-spinner" />
      <p className="loader-message">
        Processing your PDF…
      </p>
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
