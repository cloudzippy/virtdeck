import { useCallback, useEffect, useState } from "react";
import { ApiError, listVMs } from "../api/client";
import type { VMSummary } from "../api/types";

interface UseVMsResult {
  vms: VMSummary[];
  loading: boolean;
  error: string | null;
  refresh: () => void;
}

export function useVMs(): UseVMsResult {
  const [vms, setVMs] = useState<VMSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshToken, setRefreshToken] = useState(0);

  const refresh = useCallback(() => setRefreshToken((n) => n + 1), []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    listVMs()
      .then((result) => {
        if (!cancelled) {
          setVMs(result);
          setError(null);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "Failed to load VMs");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [refreshToken]);

  return { vms, loading, error, refresh };
}
