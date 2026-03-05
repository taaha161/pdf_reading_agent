import { useNavigate } from "react-router-dom";
import "./Landing.css";

export default function Landing() {
  const navigate = useNavigate();

  return (
    <div className="landing">
      <header className="landing-header">
        <h1 className="landing-title">Bank statements, sorted.</h1>
        <p className="landing-subtitle">
          Upload a PDF statement. We itemize, categorize, and let you validate with AI—then export to CSV.
        </p>
        <button
          type="button"
          className="landing-cta"
          onClick={() => navigate("/scanner")}
        >
          Process a statement
        </button>
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
          onClick={() => navigate("/scanner")}
        >
          Process a statement
        </button>
        <span className="landing-footer-name">Bank Statement Processor</span>
      </footer>
    </div>
  );
}
