import { Helmet } from "react-helmet-async";
import { useLocation } from "react-router-dom";
import { getMetaForPath, getCanonicalUrl } from "../lib/seo";

const NOINDEX_PATHS = new Set([
  "/login",
  "/signup",
  "/forgot-password",
  "/reset-password",
  "/dashboard",
  "/settings",
]);

/**
 * Sets document title, meta description, canonical URL, and og/twitter meta per route.
 * Render once inside the router (e.g. in App) so it runs on every route change.
 */
export default function PageMeta() {
  const { pathname } = useLocation();
  const meta = getMetaForPath(pathname);
  const canonical = getCanonicalUrl(pathname);
  const noindex = NOINDEX_PATHS.has(pathname);
  const ogType = meta.type ?? "website";

  const imageUrl = meta.image
    ? getCanonicalUrl("").replace(/\/$/, "") + meta.image
    : null;

  return (
    <Helmet>
      <title>{meta.title}</title>
      <meta name="description" content={meta.description} />
      {noindex && <meta name="robots" content="noindex, nofollow" />}
      {canonical && <link rel="canonical" href={canonical} />}
      {canonical && <meta property="og:url" content={canonical} />}
      <meta property="og:type" content={ogType} />
      <meta property="og:title" content={meta.title} />
      <meta property="og:description" content={meta.description} />
      {imageUrl && <meta property="og:image" content={imageUrl} />}
      {meta.publishedTime && (
        <meta property="article:published_time" content={meta.publishedTime} />
      )}
      <meta name="twitter:title" content={meta.title} />
      <meta name="twitter:description" content={meta.description} />
      {imageUrl && <meta name="twitter:image" content={imageUrl} />}
    </Helmet>
  );
}
