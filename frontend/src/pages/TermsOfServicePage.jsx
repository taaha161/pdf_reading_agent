import { Link } from "react-router-dom";
import rawContent from "./tos.html?raw";
import "./PrivacyPolicyPage.css";

export default function TermsOfServicePage() {
  return (
    <div className="privacy-policy-page">
      <div className="privacy-policy-page-header">
        <Link to="/" className="privacy-policy-back">
          ← Back to home
        </Link>
      </div>
      <article
        className="privacy-policy-content"
        dangerouslySetInnerHTML={{ __html: rawContent }}
      />
    </div>
  );
}
