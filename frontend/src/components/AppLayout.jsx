import { useState } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import logo from "../assets/pdf_to_excel_logo.png";
import settingsGear from "../assets/settings-gear.svg";
import { useAuth } from "../contexts/AuthContext";
import { useUsage } from "../contexts/UsageContext";
import { OFFERS, getOffer } from "../lib/offer";
import { FREE_ANON_PAGES, PLAN_PAGES, formatExpiry } from "../lib/pricing";
import "./AppLayout.css";

export default function AppLayout({ children }) {
  const navigate = useNavigate();
  const { user, signOut, loading: authLoading } = useAuth();
  const { usage } = useUsage();
  const email = user?.email ?? "";
  const isLoggedIn = user != null;
  // Logged-out visitors (e.g. ad traffic landing on /scanner) get a stripped-down
  // shell: no app sidebar or account menu, just the logo and log in / sign up.
  const isGuest = !authLoading && !isLoggedIn;

  // Real page numbers come from the server (anonymous free pages are counted
  // per client IP; signed-in balances live in billing).
  const trialUsed = usage?.trial_used ?? 0;
  const trialLimit = usage?.trial_limit || FREE_ANON_PAGES;
  const pagesRemaining = usage?.pages_remaining ?? 0;
  const freePages = usage?.free_pages ?? 0;
  const planPages = usage?.plan_pages ?? 0;
  const packPages = usage?.pack_pages ?? 0;
  const freeExpiry = formatExpiry(usage?.free_expires_at);
  const pagesProgress = isLoggedIn
    ? Math.min(pagesRemaining / PLAN_PAGES, 1)
    : Math.min(trialUsed / trialLimit, 1);

  const [isMobileNavOpen, setIsMobileNavOpen] = useState(false);

  // Ad-campaign offer (e.g. LinkedIn first month free) until they subscribe.
  const offer = getOffer(user);
  const showOffer = isLoggedIn && offer && usage && !usage.subscription_active;

  return (
    <div className={"app-layout" + (isGuest ? " app-layout--guest" : "")}>
      <header className="app-layout-header">
        <div className="app-layout-brand">
          <Link to="/" className="app-layout-logo-wrap" aria-label="Home">
            <span className="app-layout-logo-bg">
              <img src={logo} alt="" className="app-layout-logo" aria-hidden />
            </span>
          </Link>
          <span className="app-layout-brand-name">Bank Statement Scanner</span>
        </div>
        {isGuest ? (
          <div className="app-layout-header-actions">
            <Link to="/login" className="app-layout-guest-login">Log in</Link>
            <Link to="/signup" className="app-layout-guest-signup">Sign up free</Link>
          </div>
        ) : (
        <div className="app-layout-header-actions">
          <button
            type="button"
            className="app-layout-hamburger"
            aria-label={isMobileNavOpen ? "Close navigation" : "Open navigation"}
            aria-expanded={isMobileNavOpen}
            onClick={() => setIsMobileNavOpen((open) => !open)}
          >
            <span />
            <span />
            <span />
          </button>
          <span className="app-layout-divider" aria-hidden />
          <div className="app-layout-user-block">
            <button
              type="button"
              className="app-layout-avatar"
              onClick={() => navigate("/settings")}
              aria-label="Account settings"
              title={email}
              data-clarity-mask="true"
            >
              <img src={settingsGear} alt="" aria-hidden className="app-layout-avatar-icon" />
            </button>
          </div>
        </div>
        )}
      </header>

      <div className="app-layout-body">
        {!isGuest && (
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
          {usage && (
            <div className="app-layout-summary-card">
              {isLoggedIn ? (
                <>
                  <p className="app-layout-summary-label">Pages left</p>
                  <div className="app-layout-summary-bar-wrap">
                    <div className="app-layout-summary-bar" style={{ width: `${pagesProgress * 100}%` }} />
                  </div>
                  <p className="app-layout-summary-value"><strong>{pagesRemaining.toLocaleString()}</strong> pages</p>
                  {freePages > 0 && (
                    <p className="app-layout-summary-value">{freePages} free{freeExpiry ? ` until ${freeExpiry}` : ""}</p>
                  )}
                  {planPages > 0 && <p className="app-layout-summary-value">{planPages} on your plan</p>}
                  {packPages > 0 && <p className="app-layout-summary-value">{packPages} from page packs</p>}
                  <button type="button" className="app-layout-summary-cta" onClick={() => navigate("/settings#billing")}>
                    Get more pages
                  </button>
                </>
              ) : (
                <>
                  <p className="app-layout-summary-label">Free pages</p>
                  <div className="app-layout-summary-bar-wrap">
                    <div className="app-layout-summary-bar" style={{ width: `${pagesProgress * 100}%` }} />
                  </div>
                  <p className="app-layout-summary-value">{trialUsed} / {trialLimit} free pages used</p>
                </>
              )}
            </div>
          )}
        </aside>
        )}
        {isMobileNavOpen && !isGuest && (
          <nav className="app-layout-mobile-menu" aria-label="Mobile navigation">
            <button
              type="button"
              className="app-layout-mobile-link"
              onClick={() => { setIsMobileNavOpen(false); navigate("/dashboard"); }}
            >
              <span className="app-layout-nav-icon" aria-hidden><DashboardIcon /></span>
              <span className="app-layout-nav-text">Dashboard</span>
            </button>
            <button
              type="button"
              className="app-layout-mobile-link"
              onClick={() => { setIsMobileNavOpen(false); navigate("/scanner"); }}
            >
              <span className="app-layout-nav-icon" aria-hidden><ScanIcon /></span>
              <span className="app-layout-nav-text">Process statement</span>
            </button>
            <button
              type="button"
              className="app-layout-mobile-link"
              onClick={() => { setIsMobileNavOpen(false); navigate("/settings"); }}
            >
              <span className="app-layout-nav-icon" aria-hidden><AccountIcon /></span>
              <span className="app-layout-nav-text">Account</span>
            </button>
            {isLoggedIn && (
              <button
                type="button"
                className="app-layout-mobile-link app-layout-mobile-link--danger"
                onClick={() => { setIsMobileNavOpen(false); signOut(); navigate("/"); }}
              >
                <span className="app-layout-nav-icon" aria-hidden><LogOutIcon /></span>
                <span className="app-layout-nav-text">Log out</span>
              </button>
            )}
          </nav>
        )}
        <main className="app-layout-main">
          {showOffer && (
            <div className="app-layout-offer" role="note">
              <span>{OFFERS[offer].label}.</span>
              <Link to="/settings">{OFFERS[offer].cta}</Link>
            </div>
          )}
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
