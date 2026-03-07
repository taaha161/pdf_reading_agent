import { useNavigate } from "react-router-dom";
import logo from "../assets/pdf_to_excel_logo.png";
import { useAuth } from "../contexts/AuthContext";
import "./Landing.css";

export default function Landing() {
  const navigate = useNavigate();
  const { user, signOut } = useAuth();
  const isLoggedIn = !!user;

  return (
    <div className="landing">
      <header className="landing-header">
        {isLoggedIn && (
          <div className="landing-user-row">
            <span className="landing-user-name">{user.user_metadata?.full_name?.trim() || user.email}</span>
            <button
              type="button"
              className="landing-cta landing-cta-secondary landing-cta-small"
              onClick={() => navigate("/dashboard")}
            >
              Dashboard
            </button>
            <button
              type="button"
              className="landing-cta landing-cta-secondary landing-cta-small"
              onClick={() => { signOut(); }}
            >
              Log out
            </button>
          </div>
        )}
        <img src={logo} alt="Bank Statement PDF to Excel Converter" className="landing-logo" />
        <h1 className="landing-title">Bank statements, sorted.</h1>
        <p className="landing-subtitle">
          Upload a PDF statement. We itemize, categorize, and let you validate with AI—then export to CSV.
        </p>
        <div className="landing-cta-row">
          {isLoggedIn ? (
            <>
              <button
                type="button"
                className="landing-cta"
                onClick={() => navigate("/dashboard")}
              >
                Go to dashboard
              </button>
              <button
                type="button"
                className="landing-cta landing-cta-secondary"
                onClick={() => navigate("/scanner")}
              >
                Process a statement
              </button>
            </>
          ) : (
            <>
              <button
                type="button"
                className="landing-cta"
                onClick={() => navigate("/signup")}
              >
                Sign up
              </button>
              <span className="landing-cta-sep">or</span>
              <button
                type="button"
                className="landing-cta landing-cta-secondary"
                onClick={() => navigate("/login")}
              >
                Log in
              </button>
            </>
          )}
        </div>
      </header>

      <section className="landing-value">
        <div className="value-card">
          <span className="value-icon" aria-hidden>1</span>
          <h3>Upload PDF</h3>
          <p>Drop your bank statement PDF. We support both digital and scanned documents.</p>
        </div>
        <div className="value-card">
          <span className="value-icon" aria-hidden>2</span>
          <h3>AI categorization</h3>
          <p>Transactions are extracted and categorized automatically using AI.</p>
        </div>
        <div className="value-card">
          <span className="value-icon" aria-hidden>3</span>
          <h3>Validate & export</h3>
          <p>Chat to validate or correct categories, then download a clean CSV.</p>
        </div>
      </section>

      <footer className="landing-footer">
        <button
          type="button"
          className="landing-footer-link"
          onClick={() => navigate(isLoggedIn ? "/dashboard" : "/scanner")}
        >
          {isLoggedIn ? "Dashboard" : "Process a statement"}
        </button>
        {!isLoggedIn && (
          <button
            type="button"
            className="landing-footer-link"
            onClick={() => navigate("/login")}
          >
            Log in
          </button>
        )}
        <span className="landing-footer-name">Bank Statement Processor</span>
      </footer>
    </div>
  );
}
