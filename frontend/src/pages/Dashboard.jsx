import { useEffect } from "react";
import { Link } from "react-router-dom";
import AppLayout from "../components/AppLayout";
import { useAuth } from "../contexts/AuthContext";
import { useJobs } from "../contexts/JobsContext";
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
  const { jobs, loading, error, loadJobs, hasFetched } = useJobs();
  const displayName = user?.user_metadata?.full_name?.trim() || user?.email || "";

  useEffect(() => {
    if (accessToken) loadJobs();
  }, [accessToken, loadJobs]);

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
          <ul className="dashboard-list">
            {jobs.map((job) => (
              <li key={job.id} className="dashboard-card">
                <div className="dashboard-card-main">
                  <span className="dashboard-card-date">{formatDate(job.created_at)}</span>
                  <span className="dashboard-card-meta">
                    {job.transaction_count} transaction{job.transaction_count !== 1 ? "s" : ""}
                    {job.currency ? ` · ${job.currency}` : ""}
                  </span>
                </div>
                <Link to={`/scanner/${job.id}`} className="dashboard-card-view">
                  View
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </AppLayout>
  );
}
