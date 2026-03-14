import { useParams, useNavigate } from "react-router-dom";
import FlutterScannerEmbed from "../components/FlutterScannerEmbed";
import { useAuth } from "../contexts/AuthContext";
import "./ScannerResultsPage.css";

export default function ScannerResultsPage() {
  const { jobId } = useParams();
  const navigate = useNavigate();
  const { accessToken } = useAuth();

  if (!jobId) {
    navigate("/scanner", { replace: true });
    return null;
  }

  return (
    <div className="scanner-results-page">
      <header className="scanner-results-page__header">
        <button
          type="button"
          className="scanner-results-page__back"
          onClick={() => navigate(-1)}
          aria-label="Back"
        >
          <BackIcon />
          <span>Back</span>
        </button>
        <span className="scanner-results-page__title">Statement results</span>
      </header>
      <main className="scanner-results-page__main">
        <FlutterScannerEmbed jobId={jobId} token={accessToken ?? null} fillHeight />
      </main>
    </div>
  );
}

function BackIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M19 12H5M12 19l-7-7 7-7" />
    </svg>
  );
}
