import { defineConfig } from 'astro/config';
import mdx from '@astrojs/mdx';
import sitemap from '@astrojs/sitemap';

const SITE = process.env.PUBLIC_SITE_URL || 'https://bankstatementscanner.com';

// https://astro.build/config
export default defineConfig({
  site: SITE,
  output: 'static',
  trailingSlash: 'never',
  integrations: [
    mdx(),
    sitemap({
      // App/auth routes live on the SPA and must not appear in the marketing sitemap.
      filter: (page) =>
        !/\/(dashboard|settings|login|signup|forgot-password|reset-password|scanner)(\/|$)/.test(page),
    }),
  ],
  build: {
    // Emit /blog/slug/index.html style is avoided via trailingSlash:'never' + format:'file'
    format: 'file',
  },
});
