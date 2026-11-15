import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import { sentryVitePlugin } from '@sentry/vite-plugin'
import { writeFileSync } from 'node:fs'
import { join } from 'node:path'

// https://vite.dev/config/
// Base path: set BASE_PATH in env (e.g. /pdf_reading_agent/ for GitHub Pages).
// Public config is loaded at runtime from /api/config on Vercel (no env exposed to client).
const DEFAULT_SITE_URL = 'https://bankstatementscanner.com'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const isProd = mode === 'production'
  const siteUrl = env.VITE_PUBLIC_SITE_URL ?? ''
  const basePath = (env.BASE_PATH || '/').replace(/\/?$/, '/')
  const origin = siteUrl || DEFAULT_SITE_URL
  const ogImageUrl = `${origin.replace(/\/$/, '')}${basePath}og-image.png`

  const baseUrl = (siteUrl || DEFAULT_SITE_URL).replace(/\/$/, '') + basePath.replace(/\/?$/, '/')

  // Error monitoring: tag events with the deployed commit, and upload source maps
  // (then delete them from dist, so they're never public) only when a token is set.
  const release = env.VERCEL_GIT_COMMIT_SHA || env.SENTRY_RELEASE || ''
  const uploadSourceMaps = Boolean(env.SENTRY_AUTH_TOKEN && env.SENTRY_ORG && env.SENTRY_PROJECT)

  return {
    build: {
      sourcemap: uploadSourceMaps ? 'hidden' : false,
    },
    plugins: [
      react(),
      uploadSourceMaps &&
        sentryVitePlugin({
          authToken: env.SENTRY_AUTH_TOKEN,
          org: env.SENTRY_ORG,
          project: env.SENTRY_PROJECT,
          release: release ? { name: release } : undefined,
          sourcemaps: { filesToDeleteAfterUpload: ['./dist/**/*.map'] },
          telemetry: false,
        }),
      {
        name: 'html-seo-inject',
        transformIndexHtml(html) {
          return html
            .replace(/__VITE_PUBLIC_SITE_URL__/g, siteUrl)
            .replace(/__VITE_OG_IMAGE_URL__/g, ogImageUrl)
        },
      },
      {
        name: 'seo-static',
        closeBundle() {
          const outDir = join(process.cwd(), 'dist')
          const robots = `User-agent: *
Allow: /
Disallow: /dashboard
Disallow: /settings
Disallow: /login
Disallow: /signup
Disallow: /forgot-password
Disallow: /reset-password

Sitemap: ${baseUrl}sitemap.xml
`
          writeFileSync(join(outDir, 'robots.txt'), robots)
          // sitemap.xml is served from public/sitemap.xml (not overwritten here)
        },
      },
    ],
    base: env.BASE_PATH || '/',
    define: {
      'import.meta.env.VITE_PUBLIC_SITE_URL': JSON.stringify(env.VITE_PUBLIC_SITE_URL ?? ''),
      'import.meta.env.VITE_RELEASE': JSON.stringify(release),
      // Dev-only: inject public config from .env so /api/config is optional when running locally
      ...(!isProd && {
        'import.meta.env.PUBLIC_API_URL': JSON.stringify(env.API_URL ?? 'http://localhost:8000'),
        'import.meta.env.PUBLIC_SUPABASE_URL': JSON.stringify(env.SUPABASE_URL ?? ''),
        'import.meta.env.PUBLIC_SUPABASE_PUBLISHABLE_KEY': JSON.stringify(env.SUPABASE_PUBLISHABLE_KEY ?? env.SUPABASE_ANON_KEY ?? ''),
        'import.meta.env.PUBLIC_SUPABASE_ANON_KEY': JSON.stringify(env.SUPABASE_ANON_KEY ?? ''),
        'import.meta.env.PUBLIC_RECAPTCHA_SITE_KEY': JSON.stringify(env.RECAPTCHA_SITE_KEY ?? ''),
        'import.meta.env.PUBLIC_GOOGLE_CLIENT_ID': JSON.stringify(env.GOOGLE_CLIENT_ID ?? ''),
        'import.meta.env.PUBLIC_GOOGLE_API_KEY': JSON.stringify(env.GOOGLE_API_KEY ?? ''),
        'import.meta.env.PUBLIC_GOOGLE_APP_ID': JSON.stringify(env.GOOGLE_APP_ID ?? ''),
      }),
    },
  }
})
