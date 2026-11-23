import { defineConfig } from 'astro/config';
import mdx from '@astrojs/mdx';
import sitemap from '@astrojs/sitemap';
import vercel from '@astrojs/vercel';
import { readdirSync, readFileSync } from 'node:fs';

const SITE = process.env.PUBLIC_SITE_URL || 'https://bankstatementscanner.com';

// lastmod for content pages: blog `date` and bank-page `reviewed` frontmatter.
// Google uses lastmod when it is consistently accurate, so only dated pages get one.
function frontmatterDates(dir, field, prefix, slugField) {
  const out = new Map();
  for (const f of readdirSync(new URL(dir, import.meta.url))) {
    if (!f.endsWith('.md')) continue;
    const src = readFileSync(new URL(dir + f, import.meta.url), 'utf8');
    const date = src.match(new RegExp(`^${field}:\\s*"?([0-9-]{10})`, 'm'))?.[1];
    const slug = slugField
      ? src.match(new RegExp(`^${slugField}:\\s*"?([^"\\n]+)`, 'm'))?.[1]
      : f.replace(/\.md$/, '');
    if (date && slug) out.set(`${SITE}${prefix}${slug}`, new Date(date).toISOString());
  }
  return out;
}
const LASTMOD = new Map([
  ...frontmatterDates('./src/content/blog/', 'date', '/blog/'),
  ...frontmatterDates('./src/content/banks/', 'reviewed', '/convert/', 'slug'),
]);

// https://astro.build/config
export default defineConfig({
  site: SITE,
  output: 'static',
  adapter: vercel(),
  trailingSlash: 'never',
  integrations: [
    mdx(),
    sitemap({
      // App/auth routes live on the SPA and must not appear in the marketing sitemap.
      filter: (page) =>
        !/\/(dashboard|settings|login|signup|forgot-password|reset-password|scanner)(\/|$)/.test(page) &&
        // Paid-ad landing pages are noindex.
        !/\/lp\//.test(page) &&
        // Customer survey is noindex and only shared by email.
        !/\/survey\/?$/.test(page),
      serialize(item) {
        const lastmod = LASTMOD.get(item.url.replace(/\/$/, ''));
        return lastmod ? { ...item, lastmod } : item;
      },
    }),
  ],
});
