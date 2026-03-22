/**
 * Blog post metadata and content for the Bank Statement Scanner blog.
 * Used by BlogPage (index) and BlogPostPage (single post).
 */
export const BLOG_POSTS = [
  {
    slug: "pdf-bank-statement-to-csv-or-excel",
    title: "From PDF Bank Statement to CSV or Excel: What to Export and When",
    excerpt:
      "Compare CSV vs Excel for bank statement exports: when to use each, UTF-8 and import tips, and how clean AI extraction from PDFs makes both formats usable for bookkeeping and taxes.",
    date: "2026-03-18",
    category: "Guides",
    readTime: "8 min read",
    image: "/blog/images/pdf-bank-statement-to-csv-or-excel.jpg",
  },
  {
    slug: "speed-up-month-end-with-bank-statement-automation",
    title: "Speed Up Month-End Close With Automated Bank Statement Data",
    excerpt:
      "Speed month-end close by automating PDF statement capture and first-pass categorization—so accountants reconcile faster, scale client work, and spend time on exceptions, not data entry.",
    date: "2026-03-15",
    category: "For professionals",
    readTime: "8 min read",
    image: "/blog/images/speed-up-month-end-with-bank-statement-automation.jpg",
  },
  {
    slug: "bank-statement-pdf-layouts-and-extraction",
    title: "Why Bank Statement PDFs Look Different—and How Consistent Extraction Still Works",
    excerpt:
      "Why bank PDFs look different by issuer, common layout traps, scans vs digital PDFs, and how normalized extraction plus categorization gets you to CSV or Excel you can trust.",
    date: "2026-03-12",
    category: "Product",
    readTime: "7 min read",
    image: "/blog/images/bank-statement-pdf-layouts-and-extraction.jpg",
  },
  {
    slug: "bank-statement-scanner-for-accountants",
    title: "How Bank Statement Scanner Saves Accountants Hours Every Month",
    excerpt:
      "For accountants and bookkeepers: cut client statement re-keying with AI extraction and smart categorization, fit exports into QuickBooks or Excel, scale recurring close work, and reduce transcription errors.",
    date: "2025-03-10",
    category: "For professionals",
    readTime: "9 min read",
    /** Replace with your image: add file at public/blog/images/bank-statement-scanner-for-accountants.jpg */
    image: "/blog/images/bank-statement-scanner-for-accountants.jpg",
  },
  {
    slug: "bank-statement-scanner-for-small-businesses",
    title: "Small Business Bookkeeping Without the Headache",
    excerpt:
      "Small business bookkeeping: turn statement PDFs into categorized CSV or Excel for cash flow, tax prep, and your CPA—without building spreadsheets from scratch every month.",
    date: "2025-03-08",
    category: "For small business",
    readTime: "8 min read",
    /** Replace with your image: add file at public/blog/images/bank-statement-scanner-for-small-businesses.jpg */
    image: "/blog/images/bank-statement-scanner-for-small-businesses.jpg",
  },
  {
    slug: "bank-statement-scanner-for-personal-finance",
    title: "Take Control of Your Personal Finances with Your Bank Statements",
    excerpt:
      "Personal finance: extract and categorize bank and card PDFs, export to Excel or CSV, spot subscriptions and spending patterns, and simplify tax prep—same workflow for every institution.",
    date: "2025-03-05",
    category: "Personal finance",
    readTime: "8 min read",
    /** Replace with your image: add file at public/blog/images/bank-statement-scanner-for-personal-finance.jpg */
    image: "/blog/images/bank-statement-scanner-for-personal-finance.jpg",
  },
];

export function getPostBySlug(slug) {
  return BLOG_POSTS.find((p) => p.slug === slug) ?? null;
}
