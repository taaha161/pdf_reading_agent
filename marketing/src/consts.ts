// Central site constants — single source of truth for SEO + schema.
export const SITE_URL = (import.meta.env.PUBLIC_SITE_URL || 'https://bankstatementscanner.com').replace(/\/$/, '');
export const SITE_NAME = 'Bank Statement Scanner';
export const SITE_TAGLINE = 'Bank statements, sorted.';
export const SITE_DESCRIPTION =
  'Upload a bank statement PDF to itemize, categorize, and validate transactions with AI—then export to CSV.';
export const OG_IMAGE = `${SITE_URL}/og-image.png`;
export const SUPPORT_EMAIL = 'team@bankstatementscanner.com';
export const LEGAL_ENTITY = 'Chaudhry Abdul Rauf and Co LLC';

/** Absolute canonical URL for a path (no trailing slash except root). */
export function canonical(path: string): string {
  if (!path || path === '/') return `${SITE_URL}/`;
  return `${SITE_URL}/${path.replace(/^\/+|\/+$/g, '')}`;
}

/** Free statements per person (1 without an account, 3 total once signed up). Matches AUTH_TRIAL_LIMIT in backend/main.py. */
export const FREE_STATEMENTS = 3;
export const FREE_STATEMENTS_LABEL = `${FREE_STATEMENTS} statements free`;

/**
 * Public review profile (Trustpilot/G2). Empty = review links stay hidden.
 * Fill in once the profile exists.
 */
export const REVIEW_URL = '';

/**
 * Founder block on the homepage. Leave null to hide the section.
 * TODO(owner): fill with real details and add the photo to marketing/public/.
 */
export const FOUNDER: null | {
  name: string;
  role: string;
  photo: string; // path under /public, e.g. '/founder.jpg'
  linkedin?: string;
  story: string;
} = null;

/** Hero product video. Leave src empty to show the static demo only. */
export const HERO_VIDEO = { src: '', poster: '' };
