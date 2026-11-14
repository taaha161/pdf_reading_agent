import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { supabase } from "../lib/supabase";
import { notifyLogin, setApiAuthToken } from "../api/client";
import { trackOAuthSignupIfNew } from "../lib/trackSignup";
import { claimOfferForUser } from "../lib/offer";
import { getAttribution } from "../lib/attribution";
import { setMonitoringUser } from "../lib/monitoring";

// OAuth signups skip AuthPage's signUp() (where email signups attach
// attribution), so save it on the first sign-in of a just-created account.
const NEW_ACCOUNT_MS = 10 * 60 * 1000;
function saveAttributionIfNew(user) {
  if (!user?.id || user.user_metadata?.attribution) return;
  const age = Date.now() - Date.parse(user.created_at ?? "");
  if (!(age >= 0 && age < NEW_ACCOUNT_MS)) return;
  const attribution = getAttribution();
  if (!attribution) return;
  supabase.auth.updateUser({ data: { attribution } }).catch(() => {});
}

const AuthContext = createContext(null);

// Token the API client reads. Updated before React state so any effect that
// runs on the resulting re-render (child effects fire before parent ones)
// already sees it — otherwise a page refresh fires requests without a token.
let currentAccessToken = null;
setApiAuthToken(() => currentAccessToken);
function setCurrentSession(s) {
  currentAccessToken = s?.access_token ?? null;
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setMonitoringUser(user?.id ?? null);
  }, [user?.id]);

  const loadSession = useCallback(async () => {
    const { data: { session: s } } = await supabase.auth.getSession();
    setCurrentSession(s);
    setSession(s);
    setUser(s?.user ?? null);
    setLoading(false);
  }, []);

  useEffect(() => {
    loadSession();
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((event, s) => {
      setCurrentSession(s);
      setSession(s);
      setUser(s?.user ?? null);
      setLoading(false);
      // New Google/OAuth account → signup conversion (email signups fire in AuthPage).
      if (event === "SIGNED_IN") trackOAuthSignupIfNew(s?.user);
      // New account created during an ad visit → bind the ad offer to it.
      if (event === "SIGNED_IN") claimOfferForUser(s?.user);
      // New account → record which campaign brought it in (once).
      if (event === "SIGNED_IN") saveAttributionIfNew(s?.user);
      // Owner login notification: only on a real SIGNED_IN (not INITIAL_SESSION
      // or TOKEN_REFRESHED), deduped to once per browser session per user.
      if (event === "SIGNED_IN" && s?.user?.id && s?.access_token) {
        const key = `login_notified:${s.user.id}`;
        try {
          if (!sessionStorage.getItem(key)) {
            sessionStorage.setItem(key, "1");
            void notifyLogin(s.access_token);
          }
        } catch {
          void notifyLogin(s.access_token);
        }
      }
    });
    return () => subscription.unsubscribe();
  }, [loadSession]);

  const signOut = useCallback(async () => {
    await supabase.auth.signOut();
    setCurrentSession(null);
    setUser(null);
    setSession(null);
  }, []);

  const value = {
    user,
    session,
    loading,
    signOut,
    accessToken: session?.access_token ?? null,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
