import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { useAuth } from "./AuthContext";
import { listJobs } from "../api/client";

const JobsContext = createContext(null);

export function JobsProvider({ children }) {
  const { accessToken } = useAuth();
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [hasFetched, setHasFetched] = useState(false);

  // Clear cache when user logs out so another user doesn't see cached jobs
  useEffect(() => {
    if (!accessToken) {
      setJobs([]);
      setError(null);
      setHasFetched(false);
    }
  }, [accessToken]);

  const loadJobs = useCallback(() => {
    if (!accessToken || hasFetched) return;
    setError(null);
    setLoading(true);
    listJobs()
      .then((data) => {
        setJobs(data.jobs || []);
        setHasFetched(true);
      })
      .catch((e) => {
        setError(e.status === 401 ? "Please log in again." : e.message || "Failed to load jobs");
      })
      .finally(() => {
        setLoading(false);
      });
  }, [accessToken, hasFetched]);

  const value = {
    jobs,
    loading,
    error,
    loadJobs,
    hasFetched,
  };

  return <JobsContext.Provider value={value}>{children}</JobsContext.Provider>;
}

export function useJobs() {
  const ctx = useContext(JobsContext);
  if (!ctx) throw new Error("useJobs must be used within JobsProvider");
  return ctx;
}
