import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { useAuth } from "./AuthContext";
import { getUsage } from "../api/client";

const UsageContext = createContext(null);

/**
 * Scan-limit state for the sidebar counter. The real trial count lives in an
 * httponly cookie on the server, so it can only come from /api/usage — the
 * frontend cannot read it directly. Refetched on auth change and after each scan.
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

  // Refetch whenever auth state changes (login/logout) so the counter reflects
  // the current user (or the anonymous trial cookie).
  useEffect(() => {
    refreshUsage();
  }, [accessToken, refreshUsage]);

  return (
    <UsageContext.Provider value={{ usage, refreshUsage }}>
      {children}
    </UsageContext.Provider>
  );
}

export function useUsage() {
  const ctx = useContext(UsageContext);
  if (!ctx) throw new Error("useUsage must be used within UsageProvider");
  return ctx;
}
