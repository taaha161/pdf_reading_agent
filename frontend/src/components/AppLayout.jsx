import { Link, NavLink, useNavigate } from "react-router-dom";
import logo from "../assets/pdf_to_excel_logo.png";
import { useAuth } from "../contexts/AuthContext";
import "./AppLayout.css";

export default function AppLayout({ children }) {
  const navigate = useNavigate();
  const { user, signOut } = useAuth();
  const displayName = user?.user_metadata?.full_name?.trim() || user?.email || "Account";

  return (
    <div className="app-layout">
      <header className="app-layout-header">
        <Link to="/" className="app-layout-logo-link" aria-label="Home">
          <img src={logo} alt="" className="app-layout-logo" aria-hidden />
        </Link>
        <nav className="app-layout-nav">
          <NavLink to="/dashboard" className={({ isActive }) => "app-layout-nav-link" + (isActive ? " is-active" : "")} end>Dashboard</NavLink>
          <NavLink to="/scanner" className={({ isActive }) => "app-layout-nav-link" + (isActive ? " is-active" : "")}>Process statement</NavLink>
        </nav>
        <div className="app-layout-user">
          <span className="app-layout-user-name" title={user?.email}>{displayName}</span>
          <button
            type="button"
            className="app-layout-logout"
            onClick={() => { signOut(); navigate("/"); }}
          >
            Log out
          </button>
        </div>
      </header>
      <main className="app-layout-main">
        {children}
      </main>
    </div>
  );
}
