import { Helmet } from "react-helmet-async";
import { useLocation } from "react-router-dom";
import { getMetaForPath, getCanonicalUrl } from "../lib/seo";

/**
 * Sets document title, meta description, canonical URL, and og/twitter meta per route.
 * Render once inside the router (e.g. in App) so it runs on every route change.
 */
export default function PageMeta() {
  const { pathname } = useLocation();
  const meta = getMetaForPath(pathname);
  const canonical = getCanonicalUrl(pathname);

  return (
    <Helmet>
      <title>{meta.title}</title>
      <meta name="description" content={meta.description} />
      {canonical && <link rel="canonical" href={canonical} />}
      {canonical && <meta property="og:url" content={canonical} />}
      <meta property="og:title" content={meta.title} />
      <meta property="og:description" content={meta.description} />
      <meta name="twitter:title" content={meta.title} />
      <meta name="twitter:description" content={meta.description} />
    </Helmet>
  );
}
