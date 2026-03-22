import { Link } from "react-router-dom";
import { BLOG_POSTS } from "./blogPosts";
import "./BlogPage.css";

const PLACEHOLDER_IMAGE = "/blog/images/placeholder.svg";

export default function BlogPage() {
  return (
    <div className="blog-page">
      <header className="blog-header">
        <Link to="/" className="blog-back">
          ← Back to home
        </Link>
      </header>
      <main className="blog-main">
        <section className="blog-hero">
          <h1 className="blog-hero-title">Blog</h1>
          <p className="blog-hero-subtitle">
            How Bank Statement Scanner helps accountants, small businesses, and everyday users turn PDF statements into structured data—faster.
          </p>
        </section>
        <section className="blog-list" aria-label="Blog posts">
          {BLOG_POSTS.map((post) => (
            <article key={post.slug} className="blog-card">
              <Link to={`/blog/${post.slug}`} className="blog-card-image-link">
                <img
                  src={post.image}
                  alt=""
                  className="blog-card-image"
                  onError={(e) => { e.target.src = PLACEHOLDER_IMAGE; }}
                />
              </Link>
              <div className="blog-card-meta">
                <span className="blog-card-category">{post.category}</span>
                <span className="blog-card-date">{formatDate(post.date)}</span>
                <span className="blog-card-read">{post.readTime}</span>
              </div>
              <h2 className="blog-card-title">
                <Link to={`/blog/${post.slug}`} className="blog-card-link">
                  {post.title}
                </Link>
              </h2>
              <p className="blog-card-excerpt">{post.excerpt}</p>
              <Link to={`/blog/${post.slug}`} className="blog-card-cta">
                Read more →
              </Link>
            </article>
          ))}
        </section>
      </main>
    </div>
  );
}

function formatDate(iso) {
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" });
}
