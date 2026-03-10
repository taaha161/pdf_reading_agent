/**
 * Route → meta map for document title and description.
 * Used by PageMeta to set <title>, <meta name="description">, and canonical per route.
 */
const APP_NAME = "Bank Statement Scanner";

const defaultDescription =
  "Upload a bank statement PDF to itemize, categorize, and validate transactions with AI—then export to CSV.";

/** @type {Record<string, { title: string; description: string }>} */
export const ROUTE_META = {
  "/": {
    title: `${APP_NAME} — Bank statements, sorted.`,
    description: defaultDescription,
  },
  "/login": {
    title: `Log in — ${APP_NAME}`,
    description: "Log in to your account to access your statement jobs and dashboard.",
  },
  "/signup": {
    title: `Sign up — ${APP_NAME}`,
    description: "Create an account to save your statement jobs and access them from any device.",
  },
  "/forgot-password": {
    title: `Forgot password — ${APP_NAME}`,
    description: "Reset your password for Bank Statement Scanner.",
  },
  "/reset-password": {
    title: `Set new password — ${APP_NAME}`,
    description: "Set a new password for your account.",
  },
  "/privacy-policy": {
    title: `Privacy Policy — ${APP_NAME}`,
    description: "Privacy policy for Bank Statement Scanner. How we collect, use, and protect your data.",
  },
  "/terms-of-service": {
    title: `Terms of Service — ${APP_NAME}`,
    description: "Terms of service for Bank Statement Scanner.",
  },
  "/scanner": {
    title: `Process statement — ${APP_NAME}`,
    description: "Upload a PDF statement to itemize, categorize, and validate with AI—then export to CSV.",
  },
  "/dashboard": {
    title: `Your jobs — ${APP_NAME}`,
    description: "View and manage your past statement processing jobs.",
  },
  "/settings": {
    title: `Account settings — ${APP_NAME}`,
    description: "Manage your account settings and preferences.",
  },
};

/**
 * Get meta for a path. Handles /scanner/:jobId by returning scanner meta.
 */
export function getMetaForPath(pathname) {
  if (ROUTE_META[pathname]) return ROUTE_META[pathname];
  if (pathname.startsWith("/scanner/"))
    return ROUTE_META["/scanner"];
  return ROUTE_META["/"] ?? { title: APP_NAME, description: defaultDescription };
}

/**
 * Build full canonical URL for the current path.
 */
export function getCanonicalUrl(pathname) {
  const siteUrl =
    typeof import.meta.env.VITE_PUBLIC_SITE_URL === "string" &&
    import.meta.env.VITE_PUBLIC_SITE_URL
      ? import.meta.env.VITE_PUBLIC_SITE_URL.replace(/\/$/, "")
      : typeof window !== "undefined"
        ? window.location.origin
        : "";
  return siteUrl ? `${siteUrl}${pathname}` : "";
}
