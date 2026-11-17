import { LANDING_URL } from "../lib/seo";
import rawContent from "./privacy-policy-content.html?raw";
import "./PrivacyPolicyPage.css";

export default function PrivacyPolicyPage() {
  return (
    <div className="privacy-policy-page">
      <div className="privacy-policy-page-header">
        <a href={LANDING_URL} className="privacy-policy-back">
          ← Back to home
        </a>
      </div>
      <article
        className="privacy-policy-content"
        dangerouslySetInnerHTML={{ __html: rawContent }}
      />
    </div>
  );
}
