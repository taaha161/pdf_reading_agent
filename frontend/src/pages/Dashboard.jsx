import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import AppLayout from "../components/AppLayout";
import { useAuth } from "../contexts/AuthContext";
import AccountTimeline from "../components/AccountTimeline";
import { useJobs } from "../contexts/JobsContext";
import { deleteJobData, deleteJobsData } from "../api/client";
import { peekHandedOffFileName, takeHandedOffFile } from "../lib/fileHandoff";
import "./Dashboard.css";

const RECON_MARKS = {
  reconciled: { mark: "✓", label: "Reconciles" },
  mismatch: { mark: "✗", label: "Doesn't add up" },
};

/** ✓ / ✗ before a statement's name when it was checked; nothing when it couldn't be. */
function ReconciliationMark({ status }) {
  const m = RECON_MARKS[status];
  if (!m) return null;
  return (
    <span className={`dashboard-recon dashboard-recon--${status}`} title={m.label}>
      <span aria-hidden>{m.mark}</span>
      <span className="dashboard-table-sr-only">{m.label}: </span>
    </span>
  );
}

/** "Chase ••1234 · Mar 2026" when the statement's summary was read, else "USD statement". */
function statementLabel(job) {
  if (job.account_last4 && job.period_end) {
    const d = new Date(`${job.period_end}T00:00:00`);
    const when = Number.isNaN(d.getTime()) ? job.period_end : d.toLocaleDateString(undefined, { month: "short", year: "numeric" });
    return `${job.bank_name || "Account"} ••${job.account_last4} · ${when}`;
  }
  return `${job.currency || "Statement"} statement`;
}

function formatDate(isoString) {
  try {
    const d = new Date(isoString);
    return d.toLocaleDateString(undefined, { dateStyle: "medium" });
  } catch {
    return isoString;
  }
}

function formatMoney(value, currency) {
  if (value == null || Number.isNaN(value)) return "—";
  const code = (currency || "USD").toUpperCase();
  const symbol = code === "USD" ? "$" : code === "EUR" ? "€" : code === "GBP" ? "£" : code === "PKR" ? "Rs " : `${code} `;
  const abs = Math.abs(value);
  const formatted = abs.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return value < 0 ? `\u2212${symbol}${formatted}` : `+${symbol}${formatted}`;
}

function formatSurplus(value, currency) {
  if (value == null || Number.isNaN(value)) return "—";
  const code = (currency || "USD").toUpperCase();
  const symbol = code === "USD" ? "$" : code === "EUR" ? "€" : code === "GBP" ? "£" : code === "PKR" ? "Rs " : `${code} `;
  return `${value >= 0 ? "+" : "\u2212"}${symbol}${Math.abs(value).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export default function Dashboard() {
  const { user, accessToken } = useAuth();
  const { jobs, stats, accounts, loading, error, loadJobs, refreshJobs, hasFetched } = useJobs();
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [deleting, setDeleting] = useState(false);
  const [search, setSearch] = useState("");
  // Job ids waiting for the user to confirm deletion (inline, not a browser dialog).
  const [pendingDelete, setPendingDelete] = useState(null);
  const [deleteError, setDeleteError] = useState(null);
  const confirmBtnRef = useRef(null);
  // A statement kept in this browser while the user signed up (e.g. to use chat).
  const [pendingFileName, setPendingFileName] = useState(null);

  useEffect(() => {
    if (accessToken) loadJobs();
  }, [accessToken, loadJobs]);

  useEffect(() => {
    peekHandedOffFileName().then(setPendingFileName);
  }, []);

  useEffect(() => {
    if (pendingDelete) confirmBtnRef.current?.focus();
  }, [pendingDelete]);

  const dismissPendingFile = () => {
    takeHandedOffFile(); // deletes it from this browser
    setPendingFileName(null);
  };

  const toggleSelect = (id) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const jobsWithPayload = jobs.filter((j) => j.has_payload);
  const allSelectableSelected = jobsWithPayload.length > 0 && jobsWithPayload.every((j) => selectedIds.has(j.id));

  const toggleSelectAll = () => {
    if (allSelectableSelected) setSelectedIds(new Set());
    else setSelectedIds(new Set(jobsWithPayload.map((j) => j.id)));
  };

  const handleDeleteOne = (jobId, e) => {
    e.preventDefault();
    e.stopPropagation();
    setDeleteError(null);
    setPendingDelete([jobId]);
  };

  const handleDeleteSelected = () => {
    if (selectedIds.size === 0) return;
    setDeleteError(null);
    setPendingDelete(Array.from(selectedIds));
  };

  const confirmDelete = async () => {
    const ids = pendingDelete;
    if (!ids?.length) return;
    setDeleting(true);
    try {
      if (ids.length === 1) await deleteJobData(ids[0]);
      else await deleteJobsData(ids);
      setSelectedIds((prev) => {
        const next = new Set(prev);
        ids.forEach((id) => next.delete(id));
        return next;
      });
      setPendingDelete(null);
      refreshJobs();
    } catch (err) {
      setDeleteError(`Couldn't delete the data: ${err.message || "please try again"}. Nothing was removed.`);
    } finally {
      setDeleting(false);
    }
  };

  const filteredJobs = search.trim()
    ? jobs.filter(
        (j) =>
          formatDate(j.created_at).toLowerCase().includes(search.toLowerCase()) ||
          String(j.transaction_count).includes(search) ||
          (j.currency || "").toLowerCase().includes(search.toLowerCase())
      )
    : jobs;

  const displayName = user?.user_metadata?.full_name?.trim() || user?.email || "";

  return (
    <AppLayout>
      <div className="dashboard" data-clarity-mask="true">
        <div className="dashboard-page-header">
          <div className="dashboard-page-header-text">
            <h1 className="dashboard-title">
              {displayName ? `Hi, ${displayName}` : "Your statements"}
            </h1>
            <p className="dashboard-subtitle">
              Your converted statements. Open one to see its rows, edit them, or ask it a question.
            </p>
          </div>
          <div className="dashboard-page-header-actions">
            <Link to="/scanner" className="dashboard-btn dashboard-btn-primary">
              Convert a statement
            </Link>
          </div>
        </div>

        {error && (
          <div className="dashboard-alert" role="alert">
            {error}
            {error === "Please log in again." && (
              <p className="dashboard-alert-hint">
                <Link to="/login">Log in</Link>
              </p>
            )}
          </div>
        )}

        {pendingFileName && (
          <div className="dashboard-resume" role="status">
            <p>
              <strong>{pendingFileName}</strong> is ready to scan on your account.
            </p>
            <div className="dashboard-resume-actions">
              <Link to="/scanner?handoff=1" className="dashboard-btn dashboard-btn-primary">Scan it now</Link>
              <button type="button" className="dashboard-btn dashboard-btn-secondary" onClick={dismissPendingFile}>
                Dismiss
              </button>
            </div>
          </div>
        )}

        {!accessToken && !error && (
          <div className="dashboard-loading">Checking that you're signed in…</div>
        )}

        {accessToken && loading && !hasFetched ? (
          <div className="dashboard-loading">Loading your statements…</div>
        ) : (
          <div className="dashboard-desk">
            <AccountTimeline accounts={accounts} />
            {/* Account summary: set like the summary box on a statement */}
            <section className="dashboard-sheet dashboard-summary" aria-labelledby="dash-summary-h">
              <h2 id="dash-summary-h" className="dashboard-sheet-title">Summary</h2>
              <p className="dashboard-sheet-note">Across every saved statement</p>
              <dl className="dashboard-summary-list">
                <div>
                  <dt>Money in</dt>
                  <dd>{formatMoney(stats?.total_income, stats?.primary_currency)}</dd>
                </div>
                <div>
                  <dt>Money out</dt>
                  <dd>{stats != null ? formatMoney(-stats.total_expenses, stats.primary_currency) : "—"}</dd>
                </div>
                <div className="dashboard-summary-net">
                  <dt>Net</dt>
                  <dd>{formatSurplus(stats?.surplus ?? 0, stats?.primary_currency)}</dd>
                </div>
                <div>
                  <dt>Statements with data</dt>
                  <dd>{jobsWithPayload.length}</dd>
                </div>
              </dl>
              {stats?.summary_by_category?.length > 0 && (
                <div className="dashboard-cats">
                  <h3 className="dashboard-cats-title">Spending by category</h3>
                  {(() => {
                    const total = stats.summary_by_category.reduce((s2, c) => s2 + c.total, 0);
                    return (
                      <ul className="dashboard-cats-list" role="list">
                        {stats.summary_by_category.slice(0, 6).map(({ category, total: catTotal }) => {
                          const pct = total > 0 ? Math.round((catTotal / total) * 100) : 0;
                          return (
                            <li key={category}>
                              <span className="dashboard-cats-name">{category}</span>
                              <span className="dashboard-cats-track" aria-hidden="true">
                                <span className="dashboard-cats-fill" style={{ width: `${pct}%` }} />
                              </span>
                              <span className="dashboard-cats-pct">{pct}%</span>
                            </li>
                          );
                        })}
                      </ul>
                    );
                  })()}
                </div>
              )}
            </section>

            <section className="dashboard-sheet dashboard-statements" aria-labelledby="dash-statements-h">
              <div className="dashboard-table-header">
                <h2 id="dash-statements-h" className="dashboard-sheet-title">Statements</h2>
                {jobs.length > 0 && (
                  <input
                    type="search"
                    className="dashboard-table-search"
                    placeholder="Search by date or currency"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    aria-label="Search statements"
                  />
                )}
              </div>

              {deleteError && (
                <div className="dashboard-alert" role="alert">{deleteError}</div>
              )}

              {pendingDelete && (
                <div
                  className="dashboard-confirm"
                  role="alertdialog"
                  aria-labelledby="dashboard-confirm-text"
                  onKeyDown={(e) => e.key === "Escape" && !deleting && setPendingDelete(null)}
                >
                  <p id="dashboard-confirm-text">
                    Delete the saved transactions for{" "}
                    {pendingDelete.length === 1 ? "this statement" : `${pendingDelete.length} statements`}? This can&rsquo;t be
                    undone. {pendingDelete.length === 1 ? "The statement stays" : "They stay"} in your list and still
                    count toward pages used.
                  </p>
                  <div className="dashboard-confirm-actions">
                    <button
                      ref={confirmBtnRef}
                      type="button"
                      className="dashboard-btn dashboard-btn-danger"
                      onClick={confirmDelete}
                      disabled={deleting}
                    >
                      {deleting ? "Deleting…" : "Delete data"}
                    </button>
                    <button
                      type="button"
                      className="dashboard-btn dashboard-btn-secondary"
                      onClick={() => setPendingDelete(null)}
                      disabled={deleting}
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}

              {jobs.length === 0 ? (
                <div className="dashboard-empty">
                  <p className="dashboard-empty-title">No statements yet</p>
                  <p className="dashboard-empty-text">Convert your first bank statement and it will be kept here, ready to open again.</p>
                  <Link to="/scanner" className="dashboard-btn dashboard-btn-primary">Convert a statement</Link>
                </div>
              ) : (
                <>
                  <div className="dashboard-table-wrap">
                    <table className="dashboard-table">
                      <thead>
                        <tr>
                          <th scope="col" className="dashboard-table-cell-check">
                            <input
                              type="checkbox"
                              checked={allSelectableSelected}
                              onChange={toggleSelectAll}
                              disabled={deleting || jobsWithPayload.length === 0}
                              aria-label="Select all statements with saved data"
                            />
                          </th>
                          <th scope="col">Converted</th>
                          <th scope="col">Statement</th>
                          <th scope="col" className="dashboard-table-num">Rows</th>
                          <th scope="col"><span className="dashboard-table-sr-only">Actions</span></th>
                        </tr>
                      </thead>
                      <tbody>
                        {filteredJobs.map((job) => (
                          <tr key={job.id} className={`dashboard-table-row${job.has_payload ? "" : " is-empty"}`}>
                            <td className="dashboard-table-cell-check">
                              <input
                                type="checkbox"
                                checked={selectedIds.has(job.id)}
                                onChange={() => toggleSelect(job.id)}
                                disabled={deleting || !job.has_payload}
                                aria-label={`Select statement from ${formatDate(job.created_at)}`}
                              />
                            </td>
                            <td className="dashboard-table-date">{formatDate(job.created_at)}</td>
                            <td className="dashboard-table-desc">
                              {job.has_payload ? (
                                <Link to={`/scanner/${job.id}`} className="dashboard-table-open">
                                  <ReconciliationMark status={job.reconciliation_status} />
                                  {statementLabel(job)}
                                </Link>
                              ) : (
                                <span className="dashboard-table-gone">Data deleted or not saved (incognito)</span>
                              )}
                            </td>
                            <td className="dashboard-table-num">{job.transaction_count}</td>
                            <td className="dashboard-table-actions">
                              {job.has_payload && (
                                <>
                                  <Link to={`/scanner/${job.id}`} className="dashboard-table-action">Open</Link>
                                  <button
                                    type="button"
                                    className="dashboard-table-action-btn"
                                    onClick={(e) => handleDeleteOne(job.id, e)}
                                    disabled={deleting}
                                    aria-label={`Delete saved data for statement from ${formatDate(job.created_at)}`}
                                  >
                                    <TrashIcon />
                                  </button>
                                </>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <div className="dashboard-table-footer">
                    <p className="dashboard-table-count">
                      {filteredJobs.length === jobs.length
                        ? `${jobs.length} ${jobs.length === 1 ? "statement" : "statements"}`
                        : `${filteredJobs.length} of ${jobs.length} statements`}
                    </p>
                    {selectedIds.size > 0 && (
                      <button
                        type="button"
                        className="dashboard-btn dashboard-btn-secondary"
                        onClick={handleDeleteSelected}
                        disabled={deleting}
                      >
                        {`Delete data for ${selectedIds.size} selected`}
                      </button>
                    )}
                  </div>
                  {search && filteredJobs.length === 0 && (
                    <p className="dashboard-empty-text">No statements match &ldquo;{search}&rdquo;.</p>
                  )}
                </>
              )}
            </section>
          </div>
        )}
      </div>
    </AppLayout>
  );
}

function TrashIcon() {
  return (
    <svg width="18" height="16" viewBox="0 0 18 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M2 4h14M7 4V2a1 1 0 011-1h2a1 1 0 011 1v2M4 4v10a1 1 0 001 1h8a1 1 0 001-1V4" />
      <path d="M7 7v5M11 7v5" />
    </svg>
  );
}
