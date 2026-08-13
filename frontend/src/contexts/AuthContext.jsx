import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { supabase } from "../lib/supabase";
import { notifyLogin } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadSession = useCallback(async () => {
    const { data: { session: s } } = await supabase.auth.getSession();
    setSession(s);
    setUser(s?.user ?? null);
    setLoading(false);
  }, []);

  useEffect(() => {
    loadSession();
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((event, s) => {
      setSession(s);
      setUser(s?.user ?? null);
      setLoading(false);
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
