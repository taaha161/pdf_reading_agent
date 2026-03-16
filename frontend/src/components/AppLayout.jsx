import { Link, NavLink, useNavigate } from "react-router-dom";
import logo from "../assets/pdf_to_excel_logo.png";
import { useAuth } from "../contexts/AuthContext";
import { useJobs } from "../contexts/JobsContext";
import "./AppLayout.css";

export default function AppLayout({ children }) {
  const navigate = useNavigate();
  const { user, signOut } = useAuth();
  const { jobs } = useJobs();
  const displayName = user?.user_metadata?.full_name?.trim() || user?.email || "Account";
  const email = user?.email ?? "";
  const jobsWithPayload = jobs.filter((j) => j.has_payload);
  const scanCount = jobsWithPayload.length;
  const scanLimit = 20;
  const isLoggedIn = user != null;
  const freeScanLimit = 5;
  const scanProgress = Math.min(scanCount / scanLimit, 1);
  const freeScanProgress = Math.min(scanCount / freeScanLimit, 1);

  return (
    <div className="app-layout">
      <header className="app-layout-header">
        <div className="app-layout-brand">
          <Link to="/" className="app-layout-logo-wrap" aria-label="Home">
            <span className="app-layout-logo-bg">
              <img src={logo} alt="" className="app-layout-logo" aria-hidden />
            </span>
          </Link>
          <span className="app-layout-brand-name">Bank Statement Scanner</span>
        </div>
        <div className="app-layout-header-actions">
          <span className="app-layout-divider" aria-hidden />
          <div className="app-layout-user-block">
            <div className="app-layout-user-lines">
              <span className="app-layout-user-name">{displayName}</span>
              {email && <span className="app-layout-user-email">{email}</span>}
            </div>
            <button
              type="button"
              className="app-layout-avatar"
              onClick={() => navigate("/settings")}
              aria-label="Account settings"
              title={email}
            >
              <span className="app-layout-avatar-dot" />
            </button>
          </div>
        </div>
      </header>

      <div className="app-layout-body">
        <aside className="app-layout-sidebar">
          <nav className="app-layout-nav" aria-label="App navigation">
            <NavLink to="/dashboard" className={({ isActive }) => "app-layout-nav-link" + (isActive ? " is-active" : "")} end>
              <span className="app-layout-nav-icon" aria-hidden><DashboardIcon /></span>
              <span className="app-layout-nav-text">Dashboard</span>
            </NavLink>
            <NavLink to="/scanner" className={({ isActive }) => "app-layout-nav-link" + (isActive ? " is-active" : "")}>
              <span className="app-layout-nav-icon" aria-hidden><ScanIcon /></span>
              <span className="app-layout-nav-text">Process statement</span>
            </NavLink>
            <NavLink to="/settings" className={({ isActive }) => "app-layout-nav-link" + (isActive ? " is-active" : "")}>
              <span className="app-layout-nav-icon" aria-hidden><AccountIcon /></span>
              <span className="app-layout-nav-text">Account</span>
            </NavLink>
            <span className="app-layout-nav-spacer" />
           {isLoggedIn && (
            <button
              type="button"
              className="app-layout-nav-link app-layout-nav-link--button"
              onClick={() => { signOut(); navigate("/"); }}
            >
              <span className="app-layout-nav-icon" aria-hidden><LogOutIcon /></span>
              <span className="app-layout-nav-text">Log out</span>
            </button>
            )}
          </nav>
         {isLoggedIn && (
          <div className="app-layout-summary-card">
            <p className="app-layout-summary-label">Monthly Scan Limit</p>
              <div className="app-layout-summary-bar-wrap">
                <div className="app-layout-summary-bar" style={{ width: `${scanProgress * 100}%` }} />
              </div>
              <p className="app-layout-summary-value">{scanCount} / {scanLimit} Statements</p>
              <Link to="/scanner" className="app-layout-summary-cta">Process statement</Link>
            </div>
          )}
          {!isLoggedIn && (
            <div className="app-layout-summary-card">
            <p className="app-layout-summary-label">Free Scan Limit</p>
            <div className="app-layout-summary-bar-wrap">
              <div className="app-layout-summary-bar" style={{ width: `${freeScanProgress * 100}%` }} />
            </div>
            <p className="app-layout-summary-value">{scanCount} / {freeScanLimit} Statements</p>
            </div>
          )}
        </aside>
        <main className="app-layout-main">
          {children}
        </main>
      </div>
    </div>
  );
}

function UploadIcon() {
  return (
    <svg width="16" height="20" viewBox="0 0 16 20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M8 14V4M8 4L5 7.5M8 4l3 3.5" />
      <path d="M2 14.5v2A2.5 2.5 0 004.5 19h7A2.5 2.5 0 0014 16.5v-2" />
    </svg>
  );
}

function DashboardIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="7" height="9" rx="1" />
      <rect x="14" y="3" width="7" height="5" rx="1" />
      <rect x="14" y="12" width="7" height="9" rx="1" />
      <rect x="3" y="16" width="7" height="5" rx="1" />
    </svg>
  );
}

function ScanIcon() {
  return (
    <svg width="18" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
      <path d="M14 2v6h6M16 13H8M16 17H8M10 9H8" />
    </svg>
  );
}

function AccountIcon() {
  return (
    <svg width="22" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2" />
      <circle cx="12" cy="7" r="4" />
    </svg>
  );
}

function LogOutIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4" />
      <path d="M16 17l5-5-5-5M21 12H9" />
    </svg>
  );
}
