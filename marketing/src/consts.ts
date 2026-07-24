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
