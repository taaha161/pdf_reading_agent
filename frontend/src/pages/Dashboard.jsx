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
  const displayName = user?.user_metadata?.full_name?.trim() || user?.email || "";

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

  return (
    <AppLayout>
      <div className="dashboard">
        <div className="dashboard-head">
          {displayName && <p className="dashboard-welcome">Hi, {displayName}</p>}
          <h1 className="dashboard-title">Your jobs</h1>
          <p className="dashboard-subtitle">Past statement processing runs. Open any job to view results and chat.</p>
          <Link to="/scanner" className="dashboard-new-btn">
            Process new statement
          </Link>
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
        ) : jobs.length === 0 ? (
          <div className="dashboard-empty">
            <p className="dashboard-empty-title">No jobs yet</p>
            <p className="dashboard-empty-text">Process your first bank statement to see it here.</p>
            <Link to="/scanner" className="dashboard-empty-cta">Process a statement</Link>
          </div>
        ) : (
          <>
            <div className="dashboard-toolbar">
              <label className="dashboard-select-all">
                <input
                  type="checkbox"
                  checked={allSelectableSelected}
                  onChange={toggleSelectAll}
                  disabled={deleting || jobsWithPayload.length === 0}
                  aria-label="Select all jobs with data"
                />
                <span>Select all</span>
              </label>
              <button
                type="button"
                className="dashboard-delete-selected"
                onClick={handleDeleteSelected}
                disabled={selectedIds.size === 0 || deleting}
              >
                {deleting ? "Deleting…" : "Delete selected data"}
              </button>
            </div>
            <ul className="dashboard-list">
              {jobs.map((job) => (
                <li key={job.id} className="dashboard-card">
                  <label className="dashboard-card-checkbox">
                    <input
                      type="checkbox"
                      checked={selectedIds.has(job.id)}
                      onChange={() => toggleSelect(job.id)}
                      disabled={deleting || !job.has_payload}
                      aria-label={`Select job ${job.id}`}
                    />
                  </label>
                  <div className="dashboard-card-main">
                    <span className="dashboard-card-date">{formatDate(job.created_at)}</span>
                    <span className="dashboard-card-meta">
                      {job.transaction_count} transaction{job.transaction_count !== 1 ? "s" : ""}
                      {job.currency ? ` · ${job.currency}` : ""}
                    </span>
                  </div>
                  <div className="dashboard-card-actions">
                    {job.has_payload ? (
                      <Link to={`/scanner/${job.id}`} className="dashboard-card-view">
                        View
                      </Link>
                    ) : (
                      <span className="dashboard-card-view dashboard-card-view--disabled" title="No data (incognito or purged)">
                        View
                      </span>
                    )}
                    <button
                      type="button"
                      className="dashboard-card-delete"
                      onClick={(e) => handleDeleteOne(job.id, e)}
                      disabled={deleting || !job.has_payload}
                      title={job.has_payload ? "Delete stored data for this job" : "No data to delete (incognito or already purged)"}
                    >
                      Delete data
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          </>
        )}
      </div>
    </AppLayout>
  );
}
