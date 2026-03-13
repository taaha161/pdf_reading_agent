import { Link, useParams, Navigate } from "react-router-dom";
import { Helmet } from "react-helmet-async";
import { getPostBySlug } from "./blogPosts";
import "./BlogPage.css";

const PLACEHOLDER_IMAGE = "/blog/images/placeholder.svg";

const POST_CONTENT = {
  "bank-statement-scanner-for-accountants": {
    title: "How Bank Statement Scanner Saves Accountants Hours Every Month",
    date: "2025-03-10",
    category: "For professionals",
    readTime: "4 min read",
    body: (
      <>
        <p>
          If you’re an accountant or bookkeeper, you know the drill: clients send PDF bank and credit card statements, and you spend hours re-keying transactions into your general ledger or reconciliation tools. One missed decimal or duplicate entry can throw off a whole month. Bank Statement Scanner is built to cut that work down to minutes so you can focus on analysis and advisory instead of data entry.
        </p>
        <h2>From PDF to structured, categorized data in one step</h2>
        <p>
          Upload a client’s statement—any major bank or card issuer—and our AI extracts dates, descriptions, amounts, and running balances, then applies smart categorization so transactions are tagged by type (e.g. income, transfers, fees, merchant categories). You get a clean, categorized dataset you can export to CSV or Excel—no more copying and pasting from PDFs or building categories by hand. That means fewer errors and a consistent format every time, which makes reconciliation and audit prep much simpler.
        </p>
        <h2>Reconcile faster and scale without adding hours</h2>
        <p>
          When you have multiple clients, the hours add up. Automating statement ingestion doesn’t just save time per file; it lets you take on more clients without proportionally increasing admin work. You can run statements in batch, export to your preferred tools, and keep your workflow in one place. For firms that need audit-ready trails, having a clear, repeatable process and exportable data is a real advantage.
        </p>
        <h2>Fewer errors, better client service</h2>
        <p>
          Manual entry is a major source of reconciliation errors. When the scanner handles extraction, you’re reducing typo and transposition risk at the source. You can still review and adjust in your own systems, but you’re starting from accurate, consistent data. That means fewer client call-backs and more confidence in the numbers you sign off on.
        </p>
        <p>
          If you’re ready to spend less time on statement data entry and more on what your clients actually need from you, try Bank Statement Scanner on your next batch of statements—you can get started in minutes.
        </p>
      </>
    ),
  },
  "bank-statement-scanner-for-small-businesses": {
    title: "Small Business Bookkeeping Without the Headache",
    date: "2025-03-08",
    category: "For small business",
    readTime: "3 min read",
    body: (
      <>
        <p>
          Running a small business means wearing a lot of hats. Bookkeeping often lands on the founder or a part-time helper, and bank statements can feel like a wall of PDFs and random line items. You need clear numbers for taxes, cash flow, and decisions—without spending your whole weekend on data entry. Bank Statement Scanner is designed to give small teams exactly that: clean, exportable transaction data from your statements in minutes.
        </p>
        <h2>You run the business; the tool handles the statements</h2>
        <p>
          Upload your bank or credit card statement PDFs and get back structured data with smart categorization: dates, descriptions, amounts, balances, and transaction categories (e.g. income, expenses by type). Export to CSV or Excel so you can plug the data into your spreadsheet, accounting software, or tax prep tool. No need to manually type transactions or assign categories—the AI does it so you’re ready when your accountant or bookkeeper asks for “the numbers.”
        </p>
        <h2>Better visibility without a full-time bookkeeper</h2>
        <p>
          Many small businesses can’t justify a dedicated finance person yet. With smart categorization built in, your statement data arrives already tagged—income, expenses by type, transfers—so you can quickly see where money is going and keep an eye on cash flow. When it’s time to file taxes or talk to your CPA, you’re not scrambling; you already have organized, categorized, exportable data.
        </p>
        <h2>Simple, affordable, and fast</h2>
        <p>
          You don’t need complex setup or a long contract. Upload a statement, review the extracted data, and export. It’s built for the kind of volume a small business actually has: a few accounts, regular statements, and a need for clarity without extra cost or complexity. Give it a try with your next statement and see how much time you save.
        </p>
      </>
    ),
  },
  "bank-statement-scanner-for-personal-finance": {
    title: "Take Control of Your Personal Finances with Your Bank Statements",
    date: "2025-03-05",
    category: "Personal finance",
    readTime: "3 min read",
    body: (
      <>
        <p>
          Your bank and credit card statements hold a clear picture of where your money goes—but that picture is usually locked inside PDFs and long lists of transactions. Manually copying and categorizing everything is tedious and easy to put off. Bank Statement Scanner uses AI to turn those PDFs into structured data with smart categorization: export to CSV or Excel with transactions already tagged (e.g. groceries, subscriptions, transfers), so you can see your finances at a glance without starting from zero.
        </p>
        <h2>From statements to spending insights</h2>
        <p>
          Upload one or more statement PDFs and get back clean, categorized rows: date, description, amount, balance, and category. Smart categorization labels transactions (e.g. dining, utilities, subscriptions) so you don’t have to. Export to a format that works with your budget spreadsheet, tracking app, or tax prep. You can merge data from multiple accounts into one place and finally see the full picture—by category—without retyping or copy-pasting from each PDF.
        </p>
        <h2>Spot patterns and stay on top of your money</h2>
        <p>
          With smart categorization already applied, you can sort by category, filter by date range, and spot recurring charges or spending spikes right away. Whether you’re building a simple budget, preparing for taxes, or just want to know where your money goes, having your statement data pre-categorized is the first step. No need to build complex spreadsheets from scratch—start from the exported, categorized data and customize from there.
        </p>
        <h2>One tool for all your statement PDFs</h2>
        <p>
          Different banks and card issuers use different PDF layouts. The scanner is built to handle a wide range of formats, so you can process checking, savings, and credit card statements in one place. Upload, review, export—and spend your time on your finances instead of on data entry.
        </p>
      </>
    ),
  },
};

export default function BlogPostPage() {
  const { slug } = useParams();
  const postMeta = getPostBySlug(slug);
  const content = slug ? POST_CONTENT[slug] : null;

  if (!postMeta || !content) {
    return <Navigate to="/blog" replace />;
  }

  return (
    <div className="blog-page blog-post-page">
      <Helmet>
        <title>{content.title} | Bank Statement Scanner Blog</title>
        <meta name="description" content={postMeta.excerpt} />
      </Helmet>
      <header className="blog-header">
        <Link to="/blog" className="blog-back">
          ← Back to blog
        </Link>
      </header>
      <main className="blog-main blog-post-main">
        <article className="blog-post">
          {postMeta.image && (
            <div className="blog-post-image-wrap">
              <img
                src={postMeta.image}
                alt=""
                className="blog-post-image"
                onError={(e) => { e.target.src = PLACEHOLDER_IMAGE; }}
              />
            </div>
          )}
          <div className="blog-post-meta">
            <span className="blog-post-category">{content.category}</span>
            <time dateTime={content.date}>{formatDate(content.date)}</time>
            <span className="blog-post-read">{content.readTime}</span>
          </div>
          <h1 className="blog-post-title">{content.title}</h1>
          <div className="blog-post-body">{content.body}</div>
        </article>
        <nav className="blog-post-nav" aria-label="Blog navigation">
          <Link to="/blog" className="blog-post-nav-link">
            ← All posts
          </Link>
        </nav>
      </main>
    </div>
  );
}

function formatDate(iso) {
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" });
}
