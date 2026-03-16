import { useNavigate, Link } from "react-router-dom";
import { Helmet } from "react-helmet-async";
import logo from "../assets/pdf_to_excel_logo.png";
import { useAuth } from "../contexts/AuthContext";
import { getCanonicalUrl } from "../lib/seo";
import settingsGear from "../assets/settings-gear.svg";
import { BLOG_POSTS } from "./blogPosts";
import "./Landing.css";

const BLOG_PLACEHOLDER_IMAGE = "/blog/images/placeholder.svg";

export default function Landing() {
  const navigate = useNavigate();
  const { user, signOut } = useAuth();
  const isLoggedIn = !!user;
  const appUrl = getCanonicalUrl("/") || (typeof window !== "undefined" ? window.location.origin : "");

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "WebApplication",
    name: "Bank Statement Scanner",
    description: "Turn messy bank statements into structured data in seconds. Upload a PDF and export clean, categorized transactions to CSV or Excel.",
    applicationCategory: "FinanceApplication",
    url: appUrl,
  };

  return (
    <div className="landing">
      <Helmet>
        <script type="application/ld+json">{JSON.stringify(jsonLd)}</script>
      </Helmet>
      <header className="landing-header">
        <nav className="landing-nav" aria-label="Primary">
          <button
            type="button"
            className="landing-brand"
            onClick={() => navigate("/")}
          >
            <span className="landing-brand-icon" aria-hidden>
              <img src={logo} alt="" />
            </span>
            <span className="landing-brand-name">Bank Statement Scanner</span>
          </button>

          <div className="landing-nav-links" role="navigation" aria-label="Landing sections">
            <a className="landing-nav-link" href="#how-it-works">How it works</a>
            <a className="landing-nav-link" href="#results">Results</a>
            <a className="landing-nav-link" href="#pricing">Pricing</a>
            <Link className="landing-nav-link" to="/blog">Blog</Link>
            <a className="landing-nav-link" href="#support">Support</a>
          </div>

          <div className="landing-nav-actions">
            {!isLoggedIn && (
              <button
                type="button"
                className="landing-nav-text landing-nav-login"
                onClick={() => navigate("/login")}
              >
                Log in
              </button>
            )}
            <button
              type="button"
              className="landing-nav-cta"
              onClick={() => navigate(isLoggedIn ? "/dashboard" : "/scanner")}
            >
              {isLoggedIn ? "Go to dashboard" : "Get started free"}
            </button>
            <button
              type="button"
          
             // className="landing-user-button"
              onClick={() => navigate(isLoggedIn ? "/settings" : "/login")}
              aria-label={isLoggedIn ? "Account settings" : "Log in"}
              title={isLoggedIn ? (user.user_metadata?.full_name?.trim() || user.email) : "Log in"}
            >
               <img src={settingsGear} alt="" aria-hidden className="app-layout-avatar-icon" />
            </button>
            {isLoggedIn && (
              <button type="button" className="landing-nav-text" onClick={() => { signOut(); }}>
                Log out
              </button>
            )}
          </div>
        </nav>
      </header>

      <main className="landing-main">
        <section className="landing-hero" id="how-it-works">
          <div className="landing-hero-copy">
            <p className="landing-pill">AI-powered bank statement scanner</p>
            <h1 className="landing-title">
              Turn messy bank statements into{" "}
              <span className="landing-accent">structured data</span> in seconds.
            </h1>
            <p className="landing-subtitle">
              AI-powered extraction and smart categorization turn any bank, credit card, or PDF statement into
              clean, categorized CSVs—so you get structured data you can trust, not just raw line items.
            </p>
            <div className="landing-hero-actions">
              <button
                type="button"
                className="landing-hero-cta"
                onClick={() => navigate("/scanner")}
              >
                Get started free
              </button>
              <button
                type="button"
                className="landing-hero-ghost"
                onClick={() => navigate("/scanner")}
              >
                View sample export
              </button>
            </div>
            <div className="landing-hero-meta">
              <span>No credit card required</span>
              <span className="landing-hero-dot" aria-hidden />
              <span>Upload up to 5 statements free</span>
            </div>
            <div className="landing-hero-stats" id="results">
              <div>
                <div className="landing-hero-stat-value">12k+</div>
                <div className="landing-hero-stat-label">Finance teams</div>
              </div>
              <div>
                <div className="landing-hero-stat-value">8 hrs</div>
                <div className="landing-hero-stat-label">Saved per client</div>
              </div>
              <div>
                <div className="landing-hero-stat-value">Upto 100%</div>
                <div className="landing-hero-stat-label">Extraction accuracy</div>
              </div>
            </div>
          </div>

          <div className="landing-hero-mock">
            <div className="landing-upload-card" aria-label="Upload bank statements">
              <div className="landing-upload-header">
                <span className="landing-upload-badge">Drag &amp; drop bank statements</span>
                <span className="landing-upload-sub">PDF, scans, or photos</span>
              </div>
              <div
                className="landing-upload-dropzone"
                role="group"
                aria-label="Upload dropzone"
                onClick={() => navigate("/scanner")}
              >
                <div className="landing-upload-icon" aria-hidden>
                  <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
                    <path
                      d="M12 14V4m0 0l-3.5 3.5M12 4l3.5 3.5"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                    <path
                      d="M4 14.5v3A2.5 2.5 0 006.5 20h11A2.5 2.5 0 0020 17.5v-3"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </div>
                <div className="landing-upload-copy">
                  <div className="landing-upload-title">Drop files to get started</div>
                  <div className="landing-upload-hint">
                    Supports Chase, Wells Fargo, Amex, and 100+ more institutions.
                  </div>
                </div>
                <div className="landing-upload-actions">
                  <button
                    type="button"
                    className="landing-cta"
                    onClick={() => navigate("/scanner")}
                  >
                  Upload PDF for free
                  </button>
                  <span className="landing-upload-or" aria-hidden>
                    or
                  </span>
                  <button
                    type="button"
                    className="landing-cta landing-cta-secondary"
                    onClick={() => navigate("/scanner")}
                  >
                    Browse files
                  </button>
                </div>
                <div className="landing-upload-meta" aria-label="Upload limits">
                  <span>MAX 50MB</span>
                  <span className="landing-upload-dot" aria-hidden />
                  <span>Computer generated or photo scanned PDF ONLY</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="landing-logos" aria-label="Trusted by">
          <p className="landing-logos-label">POWERING MODERN WORKFLOWS AT</p>
          <div className="landing-logos-row">
            <span>HQ TAX</span>
            <span>CARC</span>
          </div>
        </section>

        <section className="landing-features" aria-label="Features">
          <header className="landing-features-head">
            <h2>Powerful features for seamless finance</h2>
            <p>Our AI does the heavy lifting so you can focus on making informed financial decisions.</p>
          </header>

          <div className="landing-features-grid">
            <article className="landing-feature-card">
              <div className="landing-feature-icon" aria-hidden>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                  <path d="M4 4h16v6H4z" stroke="currentColor" strokeWidth="2" />
                  <path d="M4 14h7v6H4zM13 14h7v6h-7z" stroke="currentColor" strokeWidth="2" />
                </svg>
              </div>
              <div>
                <h3 className="landing-feature-title">AI-powered extraction</h3>
                <p className="landing-feature-text">
                  Instantly pull line-item data from any computer generated or photo scanned PDF with upto 100% accuracy.
                </p>
              </div>
            </article>

            <article className="landing-feature-card">
              <div className="landing-feature-icon" aria-hidden>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                  <path d="M4 5h16M4 12h10M4 19h7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                  <circle cx="18" cy="12" r="2" stroke="currentColor" strokeWidth="2" />
                </svg>
              </div>
              <div>
                <h3 className="landing-feature-title">Smart categorization</h3>
                <p className="landing-feature-text">
                  Automatically group transactions by merchant, type and description using custom rules and AI categorization.
                </p>
              </div>
            </article>

            <article className="landing-feature-card">
              <div className="landing-feature-icon" aria-hidden>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                  <path d="M12 2L4 6v6c0 4.4 3 8.4 8 10 5-1.6 8-5.6 8-10V6z" stroke="currentColor" strokeWidth="2" />
                  <path d="M9 11.5l2 2 4-4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </div>
              <div>
                <h3 className="landing-feature-title">Secure &amp; private</h3>
                <p className="landing-feature-text">
                  Bank-grade security. Go incognito mode to protect your privacy.
                </p>
              </div>
            </article>

            <article className="landing-feature-card">
              <div className="landing-feature-icon" aria-hidden>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                  <path d="M12 3v12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                  <path d="M7 12l5 5 5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  <path d="M5 21h14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                </svg>
              </div>
              <div>
                <h3 className="landing-feature-title">Export to any format</h3>
                <p className="landing-feature-text">
                  Download your structured and categorized data as CSV or Excel.
                </p>
              </div>
            </article>
          </div>
        </section>

        <section className="landing-usecases" aria-label="Use cases">
          <article className="landing-usecard">
            <Link to="/blog/bank-statement-scanner-for-accountants" className="landing-usecard-media" aria-hidden>
              <img
                src={BLOG_POSTS[0].image}
                alt=""
                className="landing-usecard-image"
                onError={(e) => { e.target.src = BLOG_PLACEHOLDER_IMAGE; }}
              />
            </Link>
            <div className="landing-usecard-body">
              <h3>For accountants</h3>
              <p>{BLOG_POSTS[0].excerpt}</p>
              <Link to="/blog/bank-statement-scanner-for-accountants" className="landing-usecard-link">
                Learn more
              </Link>
            </div>
          </article>

          <article className="landing-usecard">
            <Link to="/blog/bank-statement-scanner-for-small-businesses" className="landing-usecard-media" aria-hidden>
              <img
                src={BLOG_POSTS[1].image}
                alt=""
                className="landing-usecard-image"
                onError={(e) => { e.target.src = BLOG_PLACEHOLDER_IMAGE; }}
              />
            </Link>
            <div className="landing-usecard-body">
              <h3>For small business</h3>
              <p>{BLOG_POSTS[1].excerpt}</p>
              <Link to="/blog/bank-statement-scanner-for-small-businesses" className="landing-usecard-link">
                Learn more
              </Link>
            </div>
          </article>

          <article className="landing-usecard">
            <Link to="/blog/bank-statement-scanner-for-personal-finance" className="landing-usecard-media" aria-hidden>
              <img
                src={BLOG_POSTS[2].image}
                alt=""
                className="landing-usecard-image"
                onError={(e) => { e.target.src = BLOG_PLACEHOLDER_IMAGE; }}
              />
            </Link>
            <div className="landing-usecard-body">
              <h3>For personal finance</h3>
              <p>{BLOG_POSTS[2].excerpt}</p>
              <Link to="/blog/bank-statement-scanner-for-personal-finance" className="landing-usecard-link">
                Learn more
              </Link>
            </div>
          </article>
        </section>

        <section className="landing-cta-band" aria-label="Call to action">
          <div className="landing-cta-band-inner">
            <h2>Ready to stop manual data entry?</h2>
            <p>Join thousands of firms who turn messy statements into clean, structured data with Bank Statement Scanner.</p>
            <div className="landing-cta-band-actions">
              <button type="button" className="landing-cta-band-btn" onClick={() => navigate("/scanner")}>
                Start scanning now
              </button>
              <span className="landing-cta-band-note">No credit card required.</span>
            </div>
          </div>
        </section>

        <section className="landing-pricing" id="pricing" aria-label="Pricing">
          <header className="landing-pricing-head">
            <h2>Simple, pay-as-you-go pricing</h2>
            <p>Subscribe monthly and $10 is added to your credit each month. Optionally top up anytime for extra credits. No long-term commitment.</p>
          </header>
          <div className="landing-pricing-grid">
            <article className="landing-price-card landing-price-card--highlight">
              <div className="landing-price-pill">Most popular</div>
              <div className="landing-price-label">Monthly subscription</div>
              <div className="landing-price-value">
                $10<span>/mo</span>
              </div>
              <p className="landing-price-tagline">$10 in credit added to your account every month. Use credits per scan—pay only for what you use.</p>
              <ul className="landing-price-list">
                <li>$10 credit added each billing cycle</li>
                <li>Credits used per scan (from &lt;1¢ to $1.50 depending on mode)</li>
                <li>Optionally top up anytime for extra credits</li>
                <li>CSV &amp; Excel export, AI categorization—cancel anytime</li>
              </ul>
              <button
                type="button"
                className="landing-price-btn"
                onClick={() => navigate(isLoggedIn ? "/settings" : "/login")}
              >
                {isLoggedIn ? "Manage subscription" : "Get started"}
              </button>
            </article>

            <article className="landing-price-card">
              <div className="landing-price-label">Optional top-up</div>
              <div className="landing-price-value landing-price-value--custom">Add credits</div>
              <p className="landing-price-tagline">Need more credits? Add a one-time top-up anytime—with or without a subscription.</p>
              <ul className="landing-price-list">
                <li>One-time credit purchases</li>
                <li>Fast mode from &lt;1¢, balanced $1, accurate $1.50 per scan</li>
                <li>Same export &amp; categorization features</li>
                <li>Works alongside your monthly plan</li>
              </ul>
              <button
                type="button"
                className="landing-price-btn landing-price-btn--outline"
                onClick={() => navigate(isLoggedIn ? "/settings" : "/login")}
              >
                {isLoggedIn ? "Add credits" : "Get started"}
              </button>
            </article>
          </div>
        </section>
      </main>

      <footer className="landing-footer">
        <div className="landing-footer-inner">
          <div className="landing-footer-top">
            <div className="landing-footer-brand">
              <span className="landing-footer-icon" aria-hidden>
                <img src={logo} alt="" />
              </span>
              <div className="landing-footer-brand-text">
                <span>Bank Statement Scanner</span>
                <p>Turn messy bank statements into structured data in seconds.</p>
              </div>
            </div>
            <div className="landing-footer-columns">
              <div className="landing-footer-col">
                <h3>Product</h3>
                <a href="#how-it-works" className="landing-footer-link">How it works</a>
                <a href="#results" className="landing-footer-link">Results</a>
                <a href="#pricing" className="landing-footer-link">Pricing</a>
                <Link to="/blog" className="landing-footer-link">Blog</Link>
              </div>
              <div className="landing-footer-col">
                <h3>Legal</h3>
                <Link to="/privacy-policy" className="landing-footer-link">Privacy Policy</Link>
                <Link to="/terms-of-service" className="landing-footer-link">Terms of Service</Link>
                <a href="#security" className="landing-footer-link" id="support">Security</a>
              </div>
              <div className="landing-footer-col">
                <h3>Support</h3>
                <a href="#help" className="landing-footer-link">Help Center</a>
                <a href="mailto:team@bankstatementscanner.com" className="landing-footer-link">Email support</a>
              </div>
            </div>
          </div>
          <div className="landing-footer-meta">
            © {new Date().getFullYear()} Bank Statement Scanner. All rights reserved.
          </div>
        </div>
      </footer>
    </div>
  );
}
