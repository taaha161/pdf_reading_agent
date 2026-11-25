import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { useAuth } from "./AuthContext";
import { getUsage } from "../api/client";

const UsageContext = createContext(null);

/**
 * Page-limit state for the sidebar counter. Anonymous free pages are tracked
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
    if (!data || (data.trial_used == null && data.pages_remaining == null)) return;
    const pick = (keys) => Object.fromEntries(keys.filter((k) => data[k] !== undefined && data[k] !== null).map((k) => [k, data[k]]));
    setUsage((prev) => ({
      authenticated: prev?.authenticated ?? false,
      subscription_active: prev?.subscription_active ?? false,
      ...prev,
      ...pick(["trial_used", "trial_limit", "trial_remaining"]),
      ...(data.pages_remaining != null
        ? { pages_remaining: data.pages_remaining, free_pages: data.free_pages ?? 0, free_expires_at: data.free_expires_at ?? null, plan_pages: data.plan_pages ?? 0, pack_pages: data.pack_pages ?? 0, frozen_pages: data.frozen_pages ?? 0 }
        : {}),
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
