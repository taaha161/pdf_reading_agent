/**
 * Blog post metadata and content for the Bank Statement Scanner blog.
 * Used by BlogPage (index) and BlogPostPage (single post).
 */
export const BLOG_POSTS = [
  {
    slug: "bank-statement-scanner-for-accountants",
    title: "How Bank Statement Scanner Saves Accountants Hours Every Month",
    excerpt: "Stop re-keying client statements. Learn how AI-powered extraction and smart categorization turn PDFs into structured, categorized data so you can reconcile faster and focus on advisory work.",
    date: "2025-03-10",
    category: "For professionals",
    readTime: "4 min read",
    /** Replace with your image: add file at public/blog/images/bank-statement-scanner-for-accountants.jpg */
    image: "/blog/images/bank-statement-scanner-for-accountants.jpg",
  },
  {
    slug: "bank-statement-scanner-for-small-businesses",
    title: "Small Business Bookkeeping Without the Headache",
    excerpt: "You run the business—you shouldn’t have to fight your bank statements. See how small teams get clean, smart-categorized transaction data in minutes, not hours.",
    date: "2025-03-08",
    category: "For small business",
    readTime: "3 min read",
    /** Replace with your image: add file at public/blog/images/bank-statement-scanner-for-small-businesses.jpg */
    image: "/blog/images/bank-statement-scanner-for-small-businesses.jpg",
  },
  {
    slug: "bank-statement-scanner-for-personal-finance",
    title: "Take Control of Your Personal Finances with Your Bank Statements",
    excerpt: "Turn your PDF statements into spending insights with AI and smart categorization. One tool to organize transactions by category, spot patterns, and stay on top of your money—without spreadsheets from scratch.",
    date: "2025-03-05",
    category: "Personal finance",
    readTime: "3 min read",
    /** Replace with your image: add file at public/blog/images/bank-statement-scanner-for-personal-finance.jpg */
    image: "/blog/images/bank-statement-scanner-for-personal-finance.jpg",
  },
];

export function getPostBySlug(slug) {
  return BLOG_POSTS.find((p) => p.slug === slug) ?? null;
}
