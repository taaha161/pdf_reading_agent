import { Link, useParams, Navigate } from "react-router-dom";
import { getPostBySlug } from "./blogPosts";
import "./BlogPage.css";

const PLACEHOLDER_IMAGE = "/blog/images/placeholder.svg";

const POST_CONTENT = {
  "pdf-bank-statement-to-csv-or-excel": {
    title: "From PDF Bank Statement to CSV or Excel: What to Export and When",
    date: "2026-03-18",
    category: "Guides",
    readTime: "8 min read",
    body: (
      <>
        <p>
          After you stop copying from PDFs by hand, the next decision is how to move structured data into the systems you already trust. Most finance workflows end in <strong>CSV</strong> or <strong>Excel</strong>—not because the format is exciting, but because every tool from spreadsheets to GL imports speaks one or both. The right choice depends on who touches the file next, how much review happens in Excel, and whether you are feeding a one-time import or an ongoing pipeline.
        </p>
        <p>
          Bank Statement Scanner is built around that handoff: you upload a bank or credit card statement PDF, we extract dates, descriptions, amounts, and balances, apply smart categorization, and let you export to CSV or Excel so the data is ready for bookkeeping, taxes, or analysis—not a cleanup project.
        </p>
        <h2>When CSV is the right choice</h2>
        <p>
          CSV is plain text—usually comma-separated, sometimes tab-separated (TSV). Rows are predictable, file sizes stay small, and imports into accounting software, databases, and scripts rarely break because of “invisible” formatting. That matters when you are appending March next to February, merging multiple accounts, or loading into a system that expects a strict column order.
        </p>
        <p>
          <strong>Reach for CSV when:</strong> you are importing into QuickBooks, Xero, NetSuite, or another GL; you are scripting reconciliation or QA checks; you need to store a minimal archive of raw transaction data; or you are handing a file to a developer or data team who will transform it further. UTF-8 CSV avoids garbled characters in international merchant names—worth confirming in your import dialog if you see odd symbols after export.
        </p>
        <h2>When Excel (XLSX) fits better</h2>
        <p>
          Excel shines when a human is the next step: sorting by category, flagging exceptions, adding notes for your bookkeeper, or building a simple pivot for management. Formulas, filters, and multiple sheets in one workbook are normal here; CSV is intentionally dumb by comparison.
        </p>
        <p>
          <strong>Use Excel when:</strong> you want to review categorization before anything is posted; you need a presentable workbook for a client or internal meeting; or you are combining this month’s export with last month’s tabs for variance analysis. You can always “Save As CSV” from Excel when a downstream system finally needs a flat file.
        </p>
        <h2>What good extraction gives you before you choose</h2>
        <p>
          The export format only helps if the underlying columns are consistent. Chasing commas inside descriptions, split amounts across lines, or wrong dates in a CSV will waste more time than choosing XLSX ever saved. Bank Statement Scanner focuses on extracting a clean table from messy PDF layouts—then applying smart categorization—so your first export is already aligned for reconciliation, not salvage.
        </p>
        <h2>Practical checklist before you import anywhere</h2>
        <p>
          Quick checks save hours later: confirm the statement period matches what you expect; spot-check a few large debits and credits against the PDF; scan for duplicate rows if you merged files; and verify category buckets make sense for your chart of accounts (you can always adjust categories in your GL after import). Our tool is designed to make those checks fast because you are working from structured rows, not a PDF zoomed to 200%.
        </p>
        <h2>How Bank Statement Scanner fits your workflow</h2>
        <p>
          Upload your PDF, review extracted transactions and categories in the app, then export to <strong>CSV or Excel</strong>—whichever matches your next step. Same product for personal use, small business books, or firm-wide client work; the difference is only which system receives the file after you export.
        </p>
      </>
    ),
  },
  "speed-up-month-end-with-bank-statement-automation": {
    title: "Speed Up Month-End Close With Automated Bank Statement Data",
    date: "2026-03-15",
    category: "For professionals",
    readTime: "8 min read",
    body: (
      <>
        <p>
          Month-end close lives or dies on complete bank and card activity. When statements still arrive as PDFs, teams default to re-keying into spreadsheets or the GL—work that does not improve judgment, only burns hours and introduces typos. The fix is not “more discipline” with copy-paste; it is a repeatable path from PDF to structured, categorized data you can reconcile and export on a predictable schedule.
        </p>
        <p>
          Bank Statement Scanner exists for that path: upload statements from your banks and card issuers, let AI extract transaction lines and balances, use smart categorization as a first pass, then export to CSV or Excel for tie-out, journal entries, or client review—without building a custom OCR pipeline in-house.
        </p>
        <h2>Where the time actually goes (and what to automate first)</h2>
        <p>
          Before you buy another checklist, split the work: <strong>data capture</strong> (getting amounts and dates right), <strong>classification</strong> (what bucket each line belongs in), and <strong>reconciliation</strong> (matching to the ledger and explaining differences). Automation wins biggest on capture and first-pass classification; humans still own policy calls, unusual transactions, and sign-off.
        </p>
        <p>
          If your team spends nights on capture—typing from PDFs—start there. When extraction is consistent, your reviewers move from “did we type this right?” to “does this belong on this account?” That is a different—and much faster—conversation.
        </p>
        <h2>Cut reconciliation time, not rigor</h2>
        <p>
          Faster close should never mean blind posting. The goal is to remove mechanical work so accountants and controllers can focus on exceptions: missing statements, timing differences, fraud alerts, and intercompany transfers. When every file lands in the same column layout with categories applied uniformly, bank recs and credit card roll-forwards get easier to script and spot-check.
        </p>
        <p>
          Use the exported file as the <strong>source of truth for the statement period</strong>, reconcile to the GL and supporting docs, and keep the PDF as legal evidence. Bank Statement Scanner helps you generate that structured layer quickly so the rec is about the business, not the keyboard.
        </p>
        <h2>Scale without linear headcount</h2>
        <p>
          Multi-entity companies and accounting firms share the same pain: more accounts means more PDFs, but headcount rarely scales 1:1 with statement volume. A workflow that ingests PDFs in batch, applies the same extraction and categorization rules, and hands off CSV or Excel to your existing tools grows with you—whether you add two entities or twenty client files in a week.
        </p>
        <h2>What to standardize across clients or subsidiaries</h2>
        <p>
          Agree on naming for exports (entity, period, last four of account), a short review checklist for large wires and payroll, and how categories map to your internal chart of accounts. Smart categorization gives you a strong default; your firm or finance team still defines how “software,” “meals,” or “owner draw” should post. Document those mappings once and reuse them every month.
        </p>
        <h2>Close with confidence</h2>
        <p>
          Speed without accuracy is just risk on a shorter timeline. Our product emphasizes reliable extraction across the messy reality of real-world statement layouts—so month twelve looks like month one. Upload, review in the app, export, reconcile—then spend the time you saved on analysis, planning, and clients—not on fixing fat-fingered debits.
        </p>
      </>
    ),
  },
  "bank-statement-pdf-layouts-and-extraction": {
    title: "Why Bank Statement PDFs Look Different—and How Consistent Extraction Still Works",
    date: "2026-03-12",
    category: "Product",
    readTime: "7 min read",
    body: (
      <>
        <p>
          If you have ever tried to copy a table out of a bank PDF, you already know the problem: columns collapse, rows jump pages, and fees live in a different section than purchases. Multiply that by every bank, credit union, and card issuer—and by digital PDFs versus phone photos of paper—and “just get the data out” stops being simple. Useful extraction is not about reading text top to bottom; it is about understanding <strong>what is a transaction row</strong> and how it maps to the fields finance actually uses.
        </p>
        <p>
          Bank Statement Scanner is designed for that reality. You upload the file; we focus on pulling dates, descriptions, amounts, and balances into a consistent structure, then layer smart categorization so you can export to CSV or Excel and get straight to review and reconciliation.
        </p>
        <h2>Layout is not the same as meaning</h2>
        <p>
          A statement PDF is a visual document. Bookkeeping needs a logical one: one row per line item (or per logical transaction), stable columns, and running balances when the bank prints them. Two PDFs can look completely different yet describe the same kind of information—that is why template-based scrapers break whenever a bank tweaks its design.
        </p>
        <p>
          What you ultimately need is <strong>normalized data</strong>: date, payee or description, debit, credit, amount, running balance where applicable, and a category that matches how you think about spend or income. The scanner’s job is to bridge messy layout → clean rows; your job is to confirm and map to your chart of accounts or personal budget.
        </p>
        <h2>Common layout traps readers hit</h2>
        <p>
          Watch for summary sections that repeat totals, interest summaries separated from everyday purchases, pending vs posted sections, and foreign-exchange or fee lines that use different formatting. Returns and chargebacks sometimes appear as positive amounts in a debit column—or the reverse—depending on the issuer. A tool that only “grabs all numbers in order” will scramble these; one built for statements treats them as part of the transaction story, not noise.
        </p>
        <h2>Scans, photos, and mixed-quality PDFs</h2>
        <p>
          Not every PDF is born from a “Print to PDF” button. Scanned paper, mobile photos, and low-resolution uploads add skew, shadows, and OCR errors. Reliable processing combines layout detection with text recognition and validation—so dates still look like dates and decimals land in the right column. That is a different problem than exporting from a clean spreadsheet, and it is why dedicated statement processing beats generic PDF-to-text converters for real bank files.
        </p>
        <h2>How we think about “consistent” for you</h2>
        <p>
          Consistent does not mean every bank uses the same PDF—it means <strong>your exports look the same every time</strong>: predictable headers, one row per transaction for reconciliation, and categories you can filter before you push data to accounting software or a budget template. You still review edge cases; you should not fight the file format first.
        </p>
        <h2>One workflow for many banks</h2>
        <p>
          Whether your statement comes from a national bank, a regional credit union, or a major card network, the workflow stays the same in Bank Statement Scanner: upload PDF, review extracted lines and smart categories, export to CSV or Excel. That consistency is what lets individuals, small businesses, and firms standardize training and quality checks instead of maintaining one-off hacks per institution.
        </p>
      </>
    ),
  },
  "bank-statement-scanner-for-accountants": {
    title: "How Bank Statement Scanner Saves Accountants Hours Every Month",
    date: "2025-03-10",
    category: "For professionals",
    readTime: "9 min read",
    body: (
      <>
        <p>
          Client statements arrive as PDFs—often late, sometimes partial, rarely in one standard format. The hidden cost is not the upload; it is everything after: opening each file, transcribing into the GL or workpaper, fixing typos, and only then doing real accounting work. Bank Statement Scanner removes that middle layer by turning statements into structured, categorized rows you can export to CSV or Excel and reconcile against the books in a fraction of the time.
        </p>
        <h2>From PDF to structured, categorized data in one step</h2>
        <p>
          Upload a client’s checking, savings, or credit card statement. Our system extracts transaction dates, descriptions, amounts, and balances from typical bank layouts, then applies <strong>smart categorization</strong> so lines are grouped in ways that match how you think about revenue, payroll, transfers, fees, and merchant spend—not just raw text.
        </p>
        <p>
          You review in the app, adjust anything that needs a human eye, and export. That beats building a new spreadsheet template for every institution or training staff on yet another “copy from PDF” workaround.
        </p>
        <h2>Fit it into your existing stack</h2>
        <p>
          Most firms are not looking to replace QuickBooks, Xero, or Excel—they need clean inputs. CSV works for imports and scripting; Excel works when preparers want to annotate, pivot, or share a review copy with a partner. Bank Statement Scanner focuses on the extraction and first-pass categorization so your team’s expertise goes into mapping to the chart of accounts and judgment calls—not keystrokes.
        </p>
        <h2>Reconcile faster and scale without adding hours</h2>
        <p>
          Time saved per statement multiplies across your client base. Batch similar tasks: download PDFs from the client portal, run them through the scanner, export, and reconcile in a focused block instead of context-switching between ten open PDFs. For growing practices, that throughput difference is the difference between hiring another data-entry role versus another reviewer or advisor.
        </p>
        <p>
          Audit and quality teams also benefit from a repeatable process: same export shape, same review checklist, less “we did it differently last quarter because the PDF looked weird.”
        </p>
        <h2>Fewer errors, better client service</h2>
        <p>
          Transcription errors show up as mysterious GL differences, delayed closes, and awkward emails. When extraction is automated, you shrink the error surface—especially on long merchant names, foreign characters, and penny amounts that are easy to mistype at 9 p.m. You still sign off on the numbers; you are just not betting accuracy on tired eyes.
        </p>
        <h2>What to tell clients (so files arrive ready)</h2>
        <p>
          Ask for <strong>full statement PDFs</strong> for the period you are closing, not screenshots of single transactions. If they use multiple cards or accounts, one PDF per account keeps exports clean. When clients know what you need, you spend less time chasing files and more time advising—which is what they actually pay for.
        </p>
        <p>
          Ready to shrink statement grunt work on your next close? Upload a real client file to Bank Statement Scanner, walk through review and export, and compare the time to your old PDF workflow—you can be running in minutes.
        </p>
      </>
    ),
  },
  "bank-statement-scanner-for-small-businesses": {
    title: "Small Business Bookkeeping Without the Headache",
    date: "2025-03-08",
    category: "For small business",
    readTime: "8 min read",
    body: (
      <>
        <p>
          In a small business, “finance” is often Sunday night with a pile of PDFs: business checking, business credit card, maybe a second card for travel. You need reliable numbers for estimated taxes, loan covenants, and paying yourself—without hiring a full-time bookkeeper before the revenue supports it. Bank Statement Scanner helps you get from PDF to organized transactions quickly: upload, review AI-extracted lines with smart categorization, export to CSV or Excel, and hand something credible to your accountant or drop it into your spreadsheet.
        </p>
        <h2>You run the business; the tool handles the statements</h2>
        <p>
          Start with the actual files your bank gives you—usually monthly PDFs. Drag them into Bank Statement Scanner; we pull out dates, descriptions, amounts, and balances and suggest categories for common spend types (think software, meals, travel, transfers). You are not starting from a blank sheet or guessing which column in the PDF was “amount” after it pasted wrong.
        </p>
        <p>
          Export to <strong>CSV</strong> when you are importing somewhere else, or <strong>Excel</strong> when you want to sort, filter, and add your own notes before you post or send to your CPA.
        </p>
        <h2>Separate business and personal (without two Sundays)</h2>
        <p>
          If you are still cleaning up mixed expenses, use categorized exports to flag obvious personal lines faster—then fix habits next month, not in a panic before April. Clear business-only exports also make it easier when you eventually move to a dedicated business card or bank account; the process stays the same: PDF in, structured data out.
        </p>
        <h2>Better visibility without a full-time bookkeeper</h2>
        <p>
          Cash flow is not just your bank balance today—it is timing: payroll, subscriptions, inventory, and taxes. When transactions are categorized, you can sum by category in Excel and see whether software or ads crept up, or whether a vendor started charging more. You still make the decisions; you are not building pivot tables from scratch from raw PDF text.
        </p>
        <h2>Work better with your accountant or bookkeeper</h2>
        <p>
          Most friction with outside help is bad data: incomplete periods, missing card statements, or spreadsheets nobody trusts. Sending a clean export plus the PDF backup gives them something they can import or review quickly—and gives you fewer back-and-forth emails asking for “last month’s Chase file again, but the full PDF.”
        </p>
        <h2>Simple workflow you can repeat every month</h2>
        <p>
          Pick a recurring day after statements post: download PDFs, run them through the scanner, spot-check large items and transfers, export. Month-over-month gets easier because you are not reinventing the process—only reviewing what changed. That rhythm is how small businesses graduate to real bookkeeping discipline without enterprise software they do not need yet.
        </p>
        <p>
          Try it on your next statement cycle: one business checking or card PDF is enough to see the time savings versus manual entry.
        </p>
      </>
    ),
  },
  "bank-statement-scanner-for-personal-finance": {
    title: "Take Control of Your Personal Finances with Your Bank Statements",
    date: "2025-03-05",
    category: "Personal finance",
    readTime: "8 min read",
    body: (
      <>
        <p>
          Personal finance “advice” often starts with “track every dollar”—but nobody talks about how long it takes to get dollars out of a PDF. If your statements live in downloads folders and your budget lives in your head, the gap is data entry. Bank Statement Scanner closes that gap: upload your bank and card PDFs, get structured rows with smart categorization, and export to CSV or Excel so you can actually sort, sum, and spot trends.
        </p>
        <h2>From statements to spending insights</h2>
        <p>
          Work one account at a time or several—checking plus two credit cards, for example. For each PDF, we extract the transaction table and label lines with useful categories (dining, groceries, subscriptions, transfers, and more). You can correct miscategorized lines in review; the goal is a strong first pass so you are editing, not typing.
        </p>
        <p>
          Export to <strong>Excel</strong> if you like filters and charts, or <strong>CSV</strong> if you feed another tool. Either way, you are building from real statement data, not rough guesses from memory.
        </p>
        <h2>Spot patterns and stay on top of your money</h2>
        <p>
          Recurring subscriptions are the classic leak: small amounts that add up because they are easy to forget. With categorized exports, sort by category or merchant keyword and scan for “streaming,” “software,” or “gym.” Do the same for dining and delivery if you are trying to trim discretionary spend—numbers beat vague intentions.
        </p>
        <p>
          Seasonal spikes (holidays, travel, back-to-school) also show up clearly when you can filter by month in a spreadsheet built from exports instead of scrolling a 40-page PDF on your phone.
        </p>
        <h2>Taxes and documentation without the shoebox</h2>
        <p>
          When you need to support deductions or HSA reimbursements, having transactions tied to dates and merchants matters. Your exported file is a practical working copy; keep the official PDFs from the bank as your source documents. Bank Statement Scanner helps you produce the structured side fast so April—or a mid-year estimate—is not a scavenger hunt.
        </p>
        <h2>One tool for all your statement PDFs</h2>
        <p>
          Institutions change layouts all the time; that should not break your workflow. Our scanner is built for varied bank and card PDFs—same steps: upload, review, export. Spend the time you save on decisions—how much to save, what to cut, what to automate—not on copying line items by hand.
        </p>
        <h2>A simple habit that sticks</h2>
        <p>
          After each statement cycle, download PDFs from your bank, run them through Bank Statement Scanner, and save one master spreadsheet (or folder of CSVs) by year. Small, repeatable beats heroic once-a-year budgeting. Start with last month’s statement and see how fast you get a useful category breakdown—no blank spreadsheet required.
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
