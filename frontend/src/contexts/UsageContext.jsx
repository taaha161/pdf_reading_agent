import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { useAuth } from "./AuthContext";
import { getUsage } from "../api/client";

const UsageContext = createContext(null);

/**
 * Scan-limit state for the sidebar counter. The real trial count is tracked
 * server-side per client IP, so it can only come from /api/usage. Refetched on auth change and after each scan.
 */
export function UsageProvider({ children }) {
  const { accessToken } = useAuth();
  const [usage, setUsage] = useState(null);

  const refreshUsage = useCallback(() => {
    return getUsage()
      .then((data) => setUsage(data))
      .catch(() => {
        /* non-critical: leave last known value, counter just won't update */
      });
  }, []);

  // Merge fresh usage returned inline by /api/process-pdf so the counter
  // updates immediately, without waiting on a follow-up /api/usage fetch.
  const applyUsage = useCallback((data) => {
    if (!data || data.trial_used == null) return;
    setUsage((prev) => ({
      authenticated: prev?.authenticated ?? false,
      subscription_active: prev?.subscription_active ?? false,
      ...prev,
      trial_used: data.trial_used,
      trial_limit: data.trial_limit ?? prev?.trial_limit ?? 1,
      trial_remaining: data.trial_remaining ?? prev?.trial_remaining ?? 0,
      ...(data.balance_cents != null ? { balance_cents: data.balance_cents } : {}),
    }));
  }, []);

  // Refetch whenever auth state changes (login/logout) so the counter reflects
  // the current user (or the anonymous per-IP trial).
  useEffect(() => {
    refreshUsage();
  }, [accessToken, refreshUsage]);

  return (
    <UsageContext.Provider value={{ usage, refreshUsage, applyUsage }}>
      {children}
    </UsageContext.Provider>
  );
}

export function useUsage() {
  const ctx = useContext(UsageContext);
  if (!ctx) throw new Error("useUsage must be used within UsageProvider");
  return ctx;
}
