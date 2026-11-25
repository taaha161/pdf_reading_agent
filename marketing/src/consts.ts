// Central site constants — single source of truth for SEO + schema.
export const SITE_URL = (import.meta.env.PUBLIC_SITE_URL || 'https://bankstatementscanner.com').replace(/\/$/, '');
export const SITE_NAME = 'Bank Statement Scanner';
export const SITE_TAGLINE = 'Convert bank statements, then ask them anything.';
export const SITE_DESCRIPTION =
  'Convert bank statement PDFs into categorized Excel or CSV, then ask the AI for any transactions (like everything from John) and download just those.';
export const OG_IMAGE = `${SITE_URL}/og-image.png?v=2`; // bump v to refresh social caches
export const SUPPORT_EMAIL = 'team@bankstatementscanner.com';
export const LEGAL_ENTITY = 'CARC Labs LLC';

/** Absolute canonical URL for a path (no trailing slash except root). */
export function canonical(path: string): string {
  if (!path || path === '/') return `${SITE_URL}/`;
  return `${SITE_URL}/${path.replace(/^\/+|\/+$/g, '')}`;
}

/**
 * Upload size limits in MB by tier. Match frontend/src/lib/fileSize.js and backend/main.py
 * (the server enforces them; /scanner shows each visitor their own limit).
 */
export const MAX_UPLOAD_MB_GUEST = 20;
export const MAX_UPLOAD_MB_FREE_ACCOUNT = 30;
export const MAX_UPLOAD_MB_PAID = 50;

/**
 * Page-based pricing. Matches backend/services/billing.py and frontend/src/lib/pricing.js.
 * A "page" is one PDF page; High accuracy mode uses ACCURATE_MULTIPLIER pages per PDF page.
 */
export const FREE_ANON_PAGES = 10; // without an account
export const FREE_SIGNUP_PAGES = 100; // free for the first month after signup, no card
export const FREE_SIGNUP_DAYS = 30;
export const PLAN_PRICE = 10; // USD per month
export const PLAN_PAGES = 150; // pages per month on the plan (reset each cycle)
export const ACCURATE_MULTIPLIER = 2;
/** Add-on packs, for monthly subscribers only. Never expire. */
export const PAGE_PACKS = [
  { pages: 10, price: 2 },
  { pages: 30, price: 5 },
  { pages: 100, price: 10 },
] as const;
export const PACKS_TEXT = PAGE_PACKS.map((p) => `${p.pages} pages for $${p.price}`).join(', ');
/** Without a subscription, pages are sold only as this one-time bulk pack. Never expires. */
export const BULK_PACK = { pages: 450, price: 49.99 } as const;
export const BULK_PACK_TEXT = `${BULK_PACK.pages} pages for $${BULK_PACK.price}`;

/** Short free-offer label for CTAs and badges. */
export const FREE_LABEL = `${FREE_SIGNUP_PAGES} pages free your first month`;
/** One-paragraph pricing answer, reused by FAQs across the site. */
export const PRICING_SUMMARY =
  `You pay per PDF page. Try ${FREE_ANON_PAGES} pages free without an account. Sign up and your first month includes ` +
  `${FREE_SIGNUP_PAGES} pages free, no credit card required. After that, the plan is $${PLAN_PRICE} a month for ` +
  `${PLAN_PAGES} pages, and subscribers can add page packs anytime: ${PACKS_TEXT} (paused if you cancel, back when you resubscribe). Not ready to subscribe? Buy ` +
  `${BULK_PACK_TEXT} once. Pack pages never expire. Cancel anytime.`;

/**
 * Official profiles of the site/company (LinkedIn page, X, Crunchbase, Product Hunt, Wikidata…).
 * Emitted as schema.org `sameAs` on the Organization/WebApplication JSON-LD and linked on /about.
 * Add only URLs that exist and that you control.
 */
export const SAME_AS: string[] = [];

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
