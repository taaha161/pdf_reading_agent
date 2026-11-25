import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { useAuth } from "./AuthContext";
import { getUsage } from "../api/client";

const UsageContext = createContext(null);

/**
 * Page-limit state for the sidebar counter. Anonymous free pages are tracked
 * server-side per client IP, so it can only come from /api/usage. Refetched on auth change and after each scan.
 */
// Last counter value per account, shown instantly on the next page load while
// /api/usage refreshes it. Per-browser convenience only; the server is the truth.
const CACHE_PREFIX = "bss_usage:";

function readCached(userId) {
  try {
    const raw = userId ? localStorage.getItem(CACHE_PREFIX + userId) : null;
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function writeCached(userId, data) {
  try {
    if (userId && data?.authenticated) localStorage.setItem(CACHE_PREFIX + userId, JSON.stringify(data));
  } catch {
    /* storage blocked or full: no cache */
  }
}

export function UsageProvider({ children }) {
  const { accessToken, loading: authLoading, user } = useAuth();
  const userId = user?.id ?? null;
  const [usage, setUsage] = useState(null);
  // Only the newest request may set usage, so a slow earlier response (e.g. the
  // signed-out one) can't overwrite a newer signed-in one.
  const requestSeq = useRef(0);
  const shownFor = useRef(undefined); // account whose counter `usage` currently holds

  const refreshUsage = useCallback(() => {
    const seq = ++requestSeq.current;
    return getUsage()
      .then((data) => {
        if (seq !== requestSeq.current) return;
        setUsage(data);
        writeCached(shownFor.current, data);
      })
      .catch(() => {
        /* non-critical: leave last known value, counter just won't update */
      });
  }, []);

  // Merge fresh usage returned inline by /api/process-pdf so the counter
  // updates immediately, without waiting on a follow-up /api/usage fetch.
  const applyUsage = useCallback((data) => {
    if (!data || (data.trial_used == null && data.pages_remaining == null)) return;
    const pick = (keys) => Object.fromEntries(keys.filter((k) => data[k] !== undefined && data[k] !== null).map((k) => [k, data[k]]));
    setUsage((prev) => {
      const next = {
        authenticated: prev?.authenticated ?? false,
        subscription_active: prev?.subscription_active ?? false,
        ...prev,
        ...pick(["trial_used", "trial_limit", "trial_remaining"]),
        ...(data.pages_remaining != null
          ? { pages_remaining: data.pages_remaining, free_pages: data.free_pages ?? 0, free_expires_at: data.free_expires_at ?? null, plan_pages: data.plan_pages ?? 0, pack_pages: data.pack_pages ?? 0, frozen_pages: data.frozen_pages ?? 0 }
          : {}),
      };
      writeCached(shownFor.current, next);
      return next;
    });
  }, []);

  // Refetch whenever auth state changes (login/logout) so the counter reflects
  // the current user (or the anonymous per-IP trial). Wait until the session is
  // restored: fetching before that asks for the signed-out counter first.
  // Show the cached value for this account meanwhile.
  useEffect(() => {
    if (authLoading) return;
    if (shownFor.current !== userId) {
      // Account changed (or first load): start from that account's cached value.
      shownFor.current = userId;
      requestSeq.current++; // drop any in-flight response for the previous account
      setUsage(userId ? readCached(userId) : null);
    }
    refreshUsage();
  }, [authLoading, accessToken, userId, refreshUsage]);

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
