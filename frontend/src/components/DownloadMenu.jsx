import { useEffect, useRef, useState } from "react";
import { exportTransactions } from "../api/client";

const OPTIONS = [
  { format: "xlsx", group: "Excel (.xlsx)" },
  { format: "csv", group: "CSV" },
];

function ChevronIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="m6 9 6 6 6-6" />
    </svg>
  );
}

/** "Download" button with CSV / Excel, with or without categories. */
export default function DownloadMenu({ transactions, onError }) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(null);
  const wrapRef = useRef(null);

  useEffect(() => {
    if (!open) return;
    const onDown = (e) => {
      if (!wrapRef.current?.contains(e.target)) setOpen(false);
    };
    const onKey = (e) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const download = async (format, includeCategories) => {
    const key = `${format}-${includeCategories}`;
    setBusy(key);
    try {
      await exportTransactions(transactions, { format, includeCategories });
      setOpen(false);
    } catch (e) {
      onError?.(e.message);
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="download-menu" ref={wrapRef}>
      <button
        type="button"
        className="download-btn download-menu-trigger"
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="menu"
        aria-expanded={open}
      >
        Download
        <ChevronIcon />
      </button>
      {open && (
        <div className="download-menu-panel" role="menu">
          {OPTIONS.map(({ format, group }) => (
            <div key={format} className="download-menu-group" role="group" aria-label={group}>
              <p className="download-menu-heading">{group}</p>
              {[true, false].map((withCategories) => {
                const key = `${format}-${withCategories}`;
                return (
                  <button
                    key={key}
                    type="button"
                    role="menuitem"
                    className="download-menu-item"
                    onClick={() => download(format, withCategories)}
                    disabled={busy !== null}
                  >
                    <span>{withCategories ? "With categories" : "Without categories"}</span>
                    {busy === key && <span className="download-menu-spinner" aria-label="Downloading" />}
                  </button>
                );
              })}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
