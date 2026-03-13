import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import AppLayout from "../components/AppLayout";
import { useAuth } from "../contexts/AuthContext";
import { useJobs } from "../contexts/JobsContext";
import { deleteJobData, deleteJobsData } from "../api/client";
import "./Dashboard.css";

function formatDate(isoString) {
  try {
    const d = new Date(isoString);
    return d.toLocaleDateString(undefined, { dateStyle: "medium" });
  } catch {
    return isoString;
  }
}

export default function Dashboard() {
  const { user, accessToken } = useAuth();
  const { jobs, loading, error, loadJobs, refreshJobs, hasFetched } = useJobs();
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [deleting, setDeleting] = useState(false);
  const [search, setSearch] = useState("");

  useEffect(() => {
    if (accessToken) loadJobs();
  }, [accessToken, loadJobs]);

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

  const handleDeleteOne = async (jobId, e) => {
    e.preventDefault();
    e.stopPropagation();
    if (!window.confirm("Delete stored data for this job? The job will remain in your list (for usage count).")) return;
    setDeleting(true);
    try {
      await deleteJobData(jobId);
      refreshJobs();
    } catch (err) {
      alert(err.message || "Failed to delete job data");
    } finally {
      setDeleting(false);
    }
  };

  const handleDeleteSelected = async () => {
    if (selectedIds.size === 0) return;
    if (!window.confirm(`Delete stored data for ${selectedIds.size} job(s)? Jobs will remain in your list (for usage count).`)) return;
    setDeleting(true);
    try {
      await deleteJobsData(Array.from(selectedIds));
      setSelectedIds(new Set());
      refreshJobs();
    } catch (err) {
      alert(err.message || "Failed to delete job data");
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
      <div className="dashboard">
        <div className="dashboard-page-header">
          <div className="dashboard-page-header-text">
            <h1 className="dashboard-title">
              {displayName ? `Hi, ${displayName}` : "Dashboard"}
            </h1>
            <p className="dashboard-subtitle">
              Past statement processing runs. Open any job to view results and chat.
            </p>
          </div>
          <div className="dashboard-page-header-actions">
            <Link to="/scanner" className="dashboard-btn dashboard-btn-secondary">
              Upload
            </Link>
            <Link to="/scanner" className="dashboard-btn dashboard-btn-primary">
              Process new statement
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

        {!accessToken && !error && (
          <div className="dashboard-loading">Checking authentication…</div>
        )}

        {accessToken && loading && !hasFetched ? (
          <div className="dashboard-loading">Loading jobs…</div>
        ) : (
          <>
            <div className="dashboard-stats">
              <div className="dashboard-stat-card">
                <div className="dashboard-stat-head">
                  <span className="dashboard-stat-label">Total Income</span>
                  <span className="dashboard-stat-badge" aria-hidden>↑</span>
                </div>
                <div className="dashboard-stat-value dashboard-stat-value--positive">+$5,240.00</div>
                <div className="dashboard-stat-meta">
                  <span>vs last month</span>
                  <span className="dashboard-stat-meta-val">+12%</span>
                </div>
              </div>
              <div className="dashboard-stat-card">
                <div className="dashboard-stat-head">
                  <span className="dashboard-stat-label">Total Expenses</span>
                  <span className="dashboard-stat-badge" aria-hidden>↓</span>
                </div>
                <div className="dashboard-stat-value dashboard-stat-value--negative">-$3,150.25</div>
                <div className="dashboard-stat-meta">
                  <span>vs last month</span>
                  <span className="dashboard-stat-meta-val">-5%</span>
                </div>
              </div>
              <div className="dashboard-stat-card">
                <div className="dashboard-stat-head">
                  <span className="dashboard-stat-label">Monthly Surplus</span>
                  <span className="dashboard-stat-badge dashboard-stat-badge--neutral" aria-hidden>→</span>
                </div>
                <div className="dashboard-stat-value">$2,089.75</div>
                <div className="dashboard-stat-meta">Monthly Surplus</div>
              </div>
              <div className="dashboard-stat-card">
                <div className="dashboard-stat-head">
                  <span className="dashboard-stat-label">AI Accuracy Rating</span>
                  <span className="dashboard-stat-badge dashboard-stat-badge--accuracy" aria-hidden>✓</span>
                </div>
                <div className="dashboard-stat-value">98%</div>
                <div className="dashboard-stat-meta">AI Accuracy Rating</div>
              </div>
            </div>

            <div className="dashboard-table-section">
              <div className="dashboard-table-header">
                <h2 className="dashboard-table-title">Transactions</h2>
                <div className="dashboard-table-search-wrap">
                  <span className="dashboard-table-search-icon" aria-hidden>⌕</span>
                  <input
                    type="search"
                    className="dashboard-table-search"
                    placeholder="Search transactions..."
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    aria-label="Search transactions"
                  />
                </div>
              </div>

              {jobs.length === 0 ? (
                <div className="dashboard-empty">
                  <p className="dashboard-empty-title">No jobs yet</p>
                  <p className="dashboard-empty-text">Process your first bank statement to see it here.</p>
                  <Link to="/scanner" className="dashboard-empty-cta">Process a statement</Link>
                </div>
              ) : (
                <>
                  <div className="dashboard-table-wrap">
                    <table className="dashboard-table">
                      <thead>
                        <tr>
                          <th><input type="checkbox" checked={allSelectableSelected} onChange={toggleSelectAll} disabled={deleting || jobsWithPayload.length === 0} aria-label="Select all" /></th>
                          <th>Date</th>
                          <th>Description</th>
                          <th>Amount</th>
                          <th>Category</th>
                          <th></th>
                        </tr>
                      </thead>
                      <tbody>
                        {filteredJobs.map((job) => (
                          <tr key={job.id}>
                            <td>
                              <input
                                type="checkbox"
                                checked={selectedIds.has(job.id)}
                                onChange={() => toggleSelect(job.id)}
                                disabled={deleting || !job.has_payload}
                                aria-label={`Select job ${job.id}`}
                              />
                            </td>
                            <td>{formatDate(job.created_at)}</td>
                            <td>
                              <div className="dashboard-table-desc">
                                <span className="dashboard-table-desc-main">Statement – {job.transaction_count} transaction{job.transaction_count !== 1 ? "s" : ""}</span>
                                <span className="dashboard-table-desc-sub">{job.currency || "Processed"}</span>
                              </div>
                            </td>
                            <td className="dashboard-table-amount">—</td>
                            <td>
                              {job.has_payload ? (
                                <Link to={`/scanner/${job.id}`} className="dashboard-table-category-btn">
                                  View
                                </Link>
                              ) : (
                                <span className="dashboard-table-category-muted">—</span>
                              )}
                            </td>
                            <td>
                              <button
                                type="button"
                                className="dashboard-table-action-btn"
                                onClick={(e) => handleDeleteOne(job.id, e)}
                                disabled={deleting || !job.has_payload}
                                aria-label="Delete job data"
                              >
                                <TrashIcon />
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <div className="dashboard-table-footer">
                    <p className="dashboard-table-pagination-info">
                      Showing {filteredJobs.length} of {jobs.length} jobs
                      {selectedIds.size > 0 && (
                        <>
                          {" · "}
                          <button
                            type="button"
                            className="dashboard-delete-selected-inline"
                            onClick={handleDeleteSelected}
                            disabled={deleting}
                          >
                            {deleting ? "Deleting…" : `Delete ${selectedIds.size} selected`}
                          </button>
                        </>
                      )}
                    </p>
                    <div className="dashboard-table-pagination">
                      <button type="button" className="dashboard-pagination-btn" disabled>Previous</button>
                      <button type="button" className="dashboard-pagination-btn">1</button>
                      <button type="button" className="dashboard-pagination-btn" disabled>Next</button>
                    </div>
                  </div>
                </>
              )}
            </div>

            <div className="dashboard-analysis">
              <div className="dashboard-analysis-card">
                <h3 className="dashboard-analysis-title">Spending by Category</h3>
                <div className="dashboard-analysis-bars">
                  <div className="dashboard-analysis-bar-row">
                    <div className="dashboard-analysis-bar-label">
                      <span>Groceries</span>
                      <span>58%</span>
                    </div>
                    <div className="dashboard-analysis-bar-track">
                      <div className="dashboard-analysis-bar-fill" style={{ width: "58%" }} />
                    </div>
                  </div>
                  <div className="dashboard-analysis-bar-row">
                    <div className="dashboard-analysis-bar-label">
                      <span>Dining</span>
                      <span>22%</span>
                    </div>
                    <div className="dashboard-analysis-bar-track">
                      <div className="dashboard-analysis-bar-fill" style={{ width: "22%" }} />
                    </div>
                  </div>
                  <div className="dashboard-analysis-bar-row">
                    <div className="dashboard-analysis-bar-label">
                      <span>Transport</span>
                      <span>12%</span>
                    </div>
                    <div className="dashboard-analysis-bar-track">
                      <div className="dashboard-analysis-bar-fill" style={{ width: "12%" }} />
                    </div>
                  </div>
                </div>
              </div>
              <div className="dashboard-analysis-card dashboard-analysis-card--cta">
                <h3 className="dashboard-analysis-title">Ready for Tax Season?</h3>
                <p className="dashboard-analysis-cta-text">
                  Export categorized statements and summaries for your accountant. One click to CSV or direct sync to your tools.
                </p>
                <Link to="/scanner" className="dashboard-analysis-cta-btn">Export for taxes</Link>
              </div>
            </div>
          </>
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
