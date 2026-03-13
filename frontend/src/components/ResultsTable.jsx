import { useState, useEffect } from "react";
import { downloadCsv } from "../api/client";
import "./ResultsTable.css";

function downloadBlob(content, filename, mimeType) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

const CATEGORY_COLORS = [
  "results-chip--income",
  "results-chip--food",
  "results-chip--housing",
  "results-chip--travel",
  "results-chip--entertainment",
  "results-chip--subscriptions",
  "results-chip--shopping",
  "results-chip--utilities",
  "results-chip--healthcare",
  "results-chip--software",
  "results-chip--default",
  "results-chip--teal",
  "results-chip--amber",
  "results-chip--rose",
];

function hashCategory(s) {
  let h = 0;
  const str = String(s).toLowerCase();
  for (let i = 0; i < str.length; i++) {
    h = (h * 31 + str.charCodeAt(i)) | 0;
  }
  return Math.abs(h);
}

function getCategoryChipClass(category) {
  if (!category) return "results-chip--muted";
  const value = String(category).toLowerCase();
  if (value.includes("income") || value.includes("salary")) return "results-chip--income";
  if (value.includes("grocery") || value.includes("food") || value.includes("dining") || value.includes("drink")) return "results-chip--food";
  if (value.includes("rent") || value.includes("housing") || value.includes("mortgage")) return "results-chip--housing";
  if (value.includes("travel") || value.includes("flight") || value.includes("transport") || value.includes("gas")) return "results-chip--travel";
  if (value.includes("entertain")) return "results-chip--entertainment";
  if (value.includes("subscription")) return "results-chip--subscriptions";
  if (value.includes("shopping") || value.includes("store") || value.includes("retail")) return "results-chip--shopping";
  if (value.includes("utilit") || value.includes("bill") || value.includes("electric") || value.includes("water")) return "results-chip--utilities";
  if (value.includes("health") || value.includes("medical") || value.includes("pharmacy")) return "results-chip--healthcare";
  if (value.includes("software") || value.includes("saas") || value.includes("internet")) return "results-chip--software";
  return CATEGORY_COLORS[hashCategory(category) % CATEGORY_COLORS.length];
}

function getAmountClass(type, amount) {
  const rawType = String(type || "").toLowerCase();
  const rawAmount = String(amount || "").trim();
  const isNegative = rawAmount.startsWith("-");
  const isPositive = rawAmount.startsWith("+");

  if (rawType === "credit" || isPositive) return "results-amount--credit";
  if (rawType === "debit" || isNegative) return "results-amount--debit";
  return "results-amount--neutral";
}

function formatAmountForDisplay(type, amount) {
  const raw = String(amount ?? "").trim();
  if (!raw || raw === "—") return "—";
  const rawType = String(type || "").toLowerCase();
  const isDebit = rawType === "debit";
  const alreadyNegative = raw.startsWith("-");
  if (isDebit && !alreadyNegative) return `-${raw}`;
  return raw;
}

function validateTransactionDraft(draft) {
  const err = {};
  const date = String(draft.date ?? "").trim();
  const description = String(draft.description ?? "").trim();
  const type = String(draft.type ?? "").toLowerCase();
  const amountRaw = String(draft.amount ?? "").trim();

  if (!date) err.date = "Date is required";
  if (!description) err.description = "Description is required";
  if (type && type !== "credit" && type !== "debit") {
    err.type = "Type must be Credit or Debit";
  }
  if (!amountRaw) {
    err.amount = "Amount is required";
  } else if (/[^0-9.]/.test(amountRaw)) {
    err.amount = "Amount can only contain numbers";
  } else {
    const dotCount = (amountRaw.match(/\./g) || []).length;
    if (dotCount > 1) {
      err.amount = "Amount must be a valid number";
    } else {
      const num = Number.parseFloat(amountRaw);
      if (Number.isNaN(num) || !Number.isFinite(num)) {
        err.amount = "Amount must be a valid number";
      }
    }
  }
  return err;
}

export default function ResultsTable({
  transactions,
  jobId,
  csvContent,
  onDownloadError,
  onTransactionChange,
  onSaveTransaction,
}) {
  const [editingIndex, setEditingIndex] = useState(null);
  const [draft, setDraft] = useState({ date: "", description: "", category: "", type: "", amount: "" });
  const [errors, setErrors] = useState({});

  const closeEditCard = () => {
    setEditingIndex(null);
    setErrors({});
  };

  useEffect(() => {
    if (editingIndex == null) return;
    const onEscape = (e) => {
      if (e.key === "Escape") closeEditCard();
    };
    document.addEventListener("keydown", onEscape);
    return () => document.removeEventListener("keydown", onEscape);
  }, [editingIndex]);

  if (!jobId) return null;

  const openEditCard = (index) => {
    const t = transactions[index];
    if (t) {
      setDraft({
        date: t.date ?? "",
        description: t.description ?? "",
        category: t.category ?? "",
        type: t.type ?? "",
        amount: t.amount ?? "",
      });
      setErrors({});
      setEditingIndex(index);
    }
  };

  const handleSaveEdit = () => {
    if (editingIndex == null) return;
    const validation = validateTransactionDraft(draft);
    if (Object.keys(validation).length > 0) {
      setErrors(validation);
      return;
    }
    setErrors({});
    if (onSaveTransaction) {
      onSaveTransaction(editingIndex, {
        date: draft.date.trim(),
        description: draft.description.trim(),
        category: (draft.category ?? "").trim(),
        type: (draft.type ?? "").trim() || undefined,
        amount: draft.amount.trim(),
      });
    } else {
      onTransactionChange?.(editingIndex, "date", draft.date.trim());
      onTransactionChange?.(editingIndex, "description", draft.description.trim());
      onTransactionChange?.(editingIndex, "category", (draft.category ?? "").trim());
      onTransactionChange?.(editingIndex, "type", (draft.type ?? "").trim());
      onTransactionChange?.(editingIndex, "amount", draft.amount.trim());
    }
    closeEditCard();
  };

  const handleDownloadCsv = async () => {
    try {
      if (csvContent != null) {
        downloadBlob(csvContent, "statement.csv", "text/csv");
      } else {
        await downloadCsv(jobId);
      }
    } catch (e) {
      onDownloadError?.(e.message);
    }
  };

  return (
    <section className="results-section">
      <div className="results-header">
        <h2>Transactions</h2>
        <div className="results-header-actions">
          {transactions?.length > 0 && (
            <button type="button" onClick={handleDownloadCsv} className="download-btn">
              Download CSV
            </button>
          )}
        </div>
      </div>
      {transactions?.length > 0 ? (
      <div className="table-wrap">
        <table className="results-table">
          <colgroup>
            <col className="results-col-date" />
            <col className="results-col-desc" />
            <col className="results-col-category" />
            <col className="results-col-amount" />
            <col className="results-col-actions" />
          </colgroup>
          <thead>
            <tr>
              <th>Date</th>
              <th>Description</th>
              <th>Category</th>
              <th>Amount</th>
              <th className="results-table-actions-col">Actions</th>
            </tr>
          </thead>
          <tbody>
            {transactions.map((t, i) => {
              const chipClass = getCategoryChipClass(t.category);
              const amountClass = getAmountClass(t.type, t.amount);
              return (
                <tr key={i} className="results-row">
                  <td className="results-cell-date">
                    <span className="results-date">{t.date || "—"}</span>
                  </td>
                  <td className="results-cell-desc">
                    <div className="results-desc-main">{t.description || "—"}</div>
                  </td>
                  <td>
                    {t.category ? (
                      <span className={`results-chip ${chipClass}`}>{t.category}</span>
                    ) : (
                      <span className="results-chip results-chip--muted">Uncategorized</span>
                    )}
                  </td>
                  <td>
                    <span className={`results-amount ${amountClass}`}>{formatAmountForDisplay(t.type, t.amount)}</span>
                  </td>
                  <td className="results-cell-actions">
                    <div className="results-cell-actions-inner">
                      <button
                        type="button"
                        className="results-row-action-btn"
                        onClick={() => openEditCard(i)}
                      >
                        Edit
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      ) : (
        <p className="results-empty">No transactions extracted. Try re-uploading the PDF or a different statement.</p>
      )}

      {editingIndex != null && (
        <div
          className="results-edit-overlay"
          onClick={closeEditCard}
          role="dialog"
          aria-modal="true"
          aria-labelledby="results-edit-card-title"
        >
          <div
            className="results-edit-card"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 id="results-edit-card-title" className="results-edit-card-title">Edit transaction</h3>
            {Object.keys(errors).length > 0 && (
              <div className="results-edit-card-errors" role="alert">
                Please fix the errors below before saving.
              </div>
            )}
            <div className="results-edit-card-fields">
              <label className="results-edit-card-label">
                <span>Date</span>
                <input
                  type="text"
                  className={`results-edit-card-input ${errors.date ? "results-edit-card-input--error" : ""}`}
                  value={draft.date}
                  onChange={(e) => setDraft((p) => ({ ...p, date: e.target.value }))}
                  aria-label="Date"
                  aria-invalid={!!errors.date}
                  aria-describedby={errors.date ? "results-edit-date-error" : undefined}
                />
                {errors.date && (
                  <span id="results-edit-date-error" className="results-edit-card-field-error">{errors.date}</span>
                )}
              </label>
              <label className="results-edit-card-label">
                <span>Description</span>
                <input
                  type="text"
                  className={`results-edit-card-input ${errors.description ? "results-edit-card-input--error" : ""}`}
                  value={draft.description}
                  onChange={(e) => setDraft((p) => ({ ...p, description: e.target.value }))}
                  aria-label="Description"
                  aria-invalid={!!errors.description}
                  aria-describedby={errors.description ? "results-edit-description-error" : undefined}
                />
                {errors.description && (
                  <span id="results-edit-description-error" className="results-edit-card-field-error">{errors.description}</span>
                )}
              </label>
              <label className="results-edit-card-label">
                <span>Category</span>
                <input
                  type="text"
                  className="results-edit-card-input"
                  value={draft.category}
                  onChange={(e) => setDraft((p) => ({ ...p, category: e.target.value }))}
                  aria-label="Category"
                />
              </label>
              <label className="results-edit-card-label">
                <span>Type</span>
                <select
                  className={`results-edit-card-input results-edit-card-select ${errors.type ? "results-edit-card-input--error" : ""}`}
                  value={draft.type}
                  onChange={(e) => setDraft((p) => ({ ...p, type: e.target.value }))}
                  aria-label="Type"
                  aria-invalid={!!errors.type}
                  aria-describedby={errors.type ? "results-edit-type-error" : undefined}
                >
                  <option value="">—</option>
                  <option value="credit">Credit</option>
                  <option value="debit">Debit</option>
                </select>
                {errors.type && (
                  <span id="results-edit-type-error" className="results-edit-card-field-error">{errors.type}</span>
                )}
              </label>
              <label className="results-edit-card-label">
                <span>Amount</span>
                <input
                  type="text"
                  className={`results-edit-card-input results-edit-card-input--amount ${errors.amount ? "results-edit-card-input--error" : ""}`}
                  value={draft.amount}
                  onChange={(e) => {
                  const v = e.target.value.replace(/[^0-9.]/g, "");
                  const firstDot = v.indexOf(".");
                  const filtered =
                    firstDot === -1
                      ? v
                      : v.slice(0, firstDot + 1) + v.slice(firstDot + 1).replace(/\./g, "");
                  setDraft((p) => ({ ...p, amount: filtered }));
                }}
                  aria-label="Amount"
                  aria-invalid={!!errors.amount}
                  aria-describedby={errors.amount ? "results-edit-amount-error" : undefined}
                />
                {errors.amount && (
                  <span id="results-edit-amount-error" className="results-edit-card-field-error">{errors.amount}</span>
                )}
              </label>
            </div>
            <div className="results-edit-card-actions">
              <button
                type="button"
                className="results-row-action-btn results-row-action-btn--ghost"
                onClick={closeEditCard}
              >
                Cancel
              </button>
              <button
                type="button"
                className="results-row-action-btn results-row-action-btn--primary"
                onClick={handleSaveEdit}
              >
                Save
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
