import { StrictMode, useState, useEffect } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { HelmetProvider } from 'react-helmet-async'
import './index.css'
import { AuthProvider } from './contexts/AuthContext'
import { JobsProvider } from './contexts/JobsContext'
import { UsageProvider } from './contexts/UsageContext'
import App from './App.jsx'
import { loadConfig, CONFIG_NETWORK_ERROR } from './lib/config'
import { initSupabase } from './lib/supabase'
import { setApiBase } from './api/client'
import { captureOfferFromUrl } from './lib/offer'
import { captureAttributionFromUrl } from './lib/attribution'

// Before routing/auth redirects can drop the query string.
captureOfferFromUrl()
captureAttributionFromUrl()

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

  if (error) {
    const isNetwork = error === CONFIG_NETWORK_ERROR;
    return (
      <div style={{ padding: '3rem 1.5rem', textAlign: 'center', fontFamily: 'system-ui, sans-serif', color: '#0f172a' }}>
        <p style={{ fontSize: '1.125rem', fontWeight: 600, margin: '0 0 0.5rem' }}>
          {isNetwork ? "Couldn't load the page" : 'Something went wrong'}
        </p>
        <p style={{ color: '#64748b', margin: '0 0 1.25rem' }}>
          {isNetwork ? error : 'Please try again in a moment.'}
        </p>
        <button
          type="button"
          onClick={() => window.location.reload()}
          style={{ background: '#2563eb', color: '#fff', border: 0, borderRadius: 8, padding: '0.7rem 1.4rem', fontSize: '1rem', fontWeight: 600, cursor: 'pointer' }}
        >
          Retry
        </button>
      </div>
    );
  }
  if (!ready) return <div style={{ padding: '2rem', textAlign: 'center' }}>Loading…</div>;

  return (
    <HelmetProvider>
      <AuthProvider>
        <JobsProvider>
          <UsageProvider>
            <App />
          </UsageProvider>
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
