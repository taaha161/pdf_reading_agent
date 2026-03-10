import { StrictMode, useState, useEffect } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { HelmetProvider } from 'react-helmet-async'
import './index.css'
import { AuthProvider } from './contexts/AuthContext'
import { JobsProvider } from './contexts/JobsContext'
import App from './App.jsx'
import { loadConfig } from './lib/config'
import { initSupabase } from './lib/supabase'
import { setApiBase } from './api/client'

function BootstrappedApp() {
  const [ready, setReady] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadConfig()
      .then((c) => {
        if (!c.supabaseUrl) {
          setError(
            "Set SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY in Vercel → Settings → Environment Variables."
          );
          return;
        }
        initSupabase(c.supabaseUrl, c.supabasePublishableKey);
        setApiBase(c.apiUrl);
        setReady(true);
      })
      .catch((e) => setError(e?.message || "Config failed"));
  }, []);

  if (error) return <div style={{ padding: '2rem', textAlign: 'center' }}>Config failed: {error}</div>;
  if (!ready) return <div style={{ padding: '2rem', textAlign: 'center' }}>Loading…</div>;

  return (
    <HelmetProvider>
      <AuthProvider>
        <JobsProvider>
          <App />
        </JobsProvider>
      </AuthProvider>
    </HelmetProvider>
  );
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <BootstrappedApp />
    </BrowserRouter>
  </StrictMode>,
)
