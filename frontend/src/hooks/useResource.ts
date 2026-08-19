import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError } from "../api/client";

export function describeError(error: unknown): string {
  if (error instanceof ApiError) return `${error.status || "network"} — ${error.detail}`;
  if (error instanceof Error) return error.message;
  return String(error);
}

export interface Resource<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
  reload: () => void;
}

export function useResource<T>(
  loader: () => Promise<T>,
  dependencies: unknown[],
  options: { enabled?: boolean } = {},
): Resource<T> {
  const enabled = options.enabled ?? true;
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [nonce, setNonce] = useState(0);
  const generation = useRef(0);

  useEffect(() => {
    if (!enabled) {
      setData(null);
      setError(null);
      setLoading(false);
      return;
    }
    const current = ++generation.current;
    setLoading(true);
    loader()
      .then((result) => {
        if (generation.current !== current) return;
        setData(result);
        setError(null);
      })
      .catch((cause: unknown) => {
        if (generation.current !== current) return;
        setData(null);
        setError(describeError(cause));
      })
      .finally(() => {
        if (generation.current === current) setLoading(false);
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...dependencies, enabled, nonce]);

  const reload = useCallback(() => setNonce((value) => value + 1), []);

  return { data, error, loading, reload };
}

export interface Action<A extends unknown[]> {
  run: (...args: A) => Promise<void>;
  pending: boolean;
  error: string | null;
  clearError: () => void;
}

export function useAction<A extends unknown[]>(
  operation: (...args: A) => Promise<unknown>,
): Action<A> {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(
    async (...args: A) => {
      setPending(true);
      setError(null);
      try {
        await operation(...args);
      } catch (cause: unknown) {
        setError(describeError(cause));
      } finally {
        setPending(false);
      }
    },
    [operation],
  );

  return { run, pending, error, clearError: useCallback(() => setError(null), []) };
}
