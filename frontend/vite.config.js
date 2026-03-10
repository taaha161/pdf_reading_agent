import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import { writeFileSync } from 'node:fs'
import { join } from 'node:path'

// https://vite.dev/config/
// Base path: set BASE_PATH in env (e.g. /pdf_reading_agent/ for GitHub Pages).
// Public config is loaded at runtime from /api/config on Vercel (no env exposed to client).
const DEFAULT_SITE_URL = 'https://bankstatementscanner.com'
const PUBLIC_PATHS = ['/', '/login', '/signup', '/privacy-policy', '/terms-of-service', '/scanner']

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const isProd = mode === 'production'
  const siteUrl = env.VITE_PUBLIC_SITE_URL ?? ''
  const basePath = (env.BASE_PATH || '/').replace(/\/?$/, '/')
  const ogImageUrl = siteUrl ? `${siteUrl.replace(/\/$/, '')}${basePath}og-image.png` : ''

  const baseUrl = (siteUrl || DEFAULT_SITE_URL).replace(/\/$/, '') + basePath.replace(/\/?$/, '/')

  return {
    plugins: [
      react(),
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

Sitemap: ${baseUrl}sitemap.xml
`
          writeFileSync(join(outDir, 'robots.txt'), robots)
          const sitemap = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${PUBLIC_PATHS.map((p) => `  <url><loc>${baseUrl.replace(/\/$/, '')}${p === '/' ? '' : p}</loc></url>`).join('\n')}
</urlset>
`
          writeFileSync(join(outDir, 'sitemap.xml'), sitemap)
        },
      },
    ],
    base: env.BASE_PATH || '/',
    define: {
      'import.meta.env.VITE_PUBLIC_SITE_URL': JSON.stringify(env.VITE_PUBLIC_SITE_URL ?? ''),
      // Dev-only: inject public config from .env so /api/config is optional when running locally
      ...(!isProd && {
        'import.meta.env.PUBLIC_API_URL': JSON.stringify(env.API_URL ?? 'http://localhost:8000'),
        'import.meta.env.PUBLIC_SUPABASE_URL': JSON.stringify(env.SUPABASE_URL ?? ''),
        'import.meta.env.PUBLIC_SUPABASE_PUBLISHABLE_KEY': JSON.stringify(env.SUPABASE_PUBLISHABLE_KEY ?? env.SUPABASE_ANON_KEY ?? ''),
        'import.meta.env.PUBLIC_SUPABASE_ANON_KEY': JSON.stringify(env.SUPABASE_ANON_KEY ?? ''),
      }),
    },
  }
})
