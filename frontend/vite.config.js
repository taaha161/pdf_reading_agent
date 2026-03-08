import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
// Base path: set BASE_PATH in env (e.g. /pdf_reading_agent/ for GitHub Pages).
// Public config is loaded at runtime from /api/config on Vercel (no env exposed to client).
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const isProd = mode === 'production'

  return {
    plugins: [react()],
    base: env.BASE_PATH || '/',
    define: {
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
