import { Link } from "react-router-dom";
import logo from "../assets/pdf_to_excel_logo.png";
import "./SignupLayout.css";

const Check = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" aria-hidden>
    <path d="m5 12 5 5 9-10" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

const ICONS = {
  lock: <path d="M7 11V8a5 5 0 0 1 10 0v3M6 11h12v9H6z" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />,
  trash: <path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />,
  card: <path d="M3 6h18v12H3zM3 10h18M7 15h4" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />,
};

/**
 * Split page for signup and the paid-signup welcome: value panel + form card.
 * Desktop: panel left, form right. Mobile: form first, panel below.
 */
export default function SignupLayout({ aside, children, headerAction }) {
  return (
    <div className="su-page">
      <header className="su-header">
        <Link to="/" className="su-logo">
          <img src={logo} alt="" width="28" height="28" />
          <span>Bank Statement Scanner</span>
        </Link>
        {headerAction !== undefined ? headerAction : (
          <p className="su-header-action">
            <span className="su-hide-sm">Already have an account?</span> <Link to="/login">Log in</Link>
          </p>
        )}
      </header>
      <main className="su-main">
        <section className="su-form-col">
          <div className="su-card">{children}</div>
        </section>
        <aside className="su-aside">
          <div className="su-aside-inner">{aside}</div>
        </aside>
      </main>
    </div>
  );
}

/** Left-panel content: eyebrow, headline, lead, then anything else. */
export function ValuePanel({ eyebrow, title, lead, children }) {
  return (
    <>
      {eyebrow && <p className="su-eyebrow">{eyebrow}</p>}
      <h1 className="su-aside-title">{title}</h1>
      {lead && <p className="su-aside-lead">{lead}</p>}
      {children}
    </>
  );
}

export function BenefitList({ items }) {
  return (
    <ul className="su-benefits">
      {items.map((text) => (
        <li key={text}>
          <span className="su-benefit-icon"><Check /></span>
          {text}
        </li>
      ))}
    </ul>
  );
}

/** Security points; wording matches the /security page. */
export function SecurityList() {
  const items = [
    ["lock", "Encrypted in transit (HTTPS)"],
    ["trash", "Delete your data anytime"],
    ["card", "Payments by Stripe. We never see your card"],
  ];
  return (
    <ul className="su-security" aria-label="Security">
      {items.map(([icon, text]) => (
        <li key={icon}>
          <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden>{ICONS[icon]}</svg>
          {text}
        </li>
      ))}
    </ul>
  );
}

