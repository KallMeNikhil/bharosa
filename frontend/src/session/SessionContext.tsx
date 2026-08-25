import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

import { setCredential } from "../api/client";
import { CAPABILITIES } from "../api/types";
import type { Capability } from "../api/types";

export interface Session {
  manufacturerId: string;
  manufacturerName: string;
  actorId: string;
  capabilities: Capability[];
}

const STORAGE_KEY = "bharosa.session";

const EMPTY_SESSION: Session = {
  manufacturerId: "",
  manufacturerName: "",
  actorId: "",
  capabilities: [],
};

function buildCredential(session: Session): string | null {
  if (!session.manufacturerId || !session.actorId) return null;
  const capabilities = session.capabilities.length === CAPABILITIES.length
    ? "*"
    : session.capabilities.join(",");
  return `dev:${session.manufacturerId}:${session.actorId}:${capabilities}`;
}

function readStoredSession(): Session {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return EMPTY_SESSION;
    const parsed = JSON.parse(raw) as Partial<Session>;
    return {
      manufacturerId: parsed.manufacturerId ?? "",
      manufacturerName: parsed.manufacturerName ?? "",
      actorId: parsed.actorId ?? "",
      capabilities: (parsed.capabilities ?? []).filter((value): value is Capability =>
        (CAPABILITIES as readonly string[]).includes(value),
      ),
    };
  } catch {
    return EMPTY_SESSION;
  }
}

interface SessionContextValue {
  session: Session;
  credential: string | null;
  isConfigured: boolean;
  can: (capability: Capability) => boolean;
  update: (patch: Partial<Session>) => void;
  reset: () => void;
}

const SessionContext = createContext<SessionContextValue | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session>(readStoredSession);

  const credential = useMemo(() => {
    const value = buildCredential(session);
    setCredential(value);
    return value;
  }, [session]);

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
  }, [session]);

  const update = useCallback((patch: Partial<Session>) => {
    setSession((current) => ({ ...current, ...patch }));
  }, []);

  const reset = useCallback(() => setSession(EMPTY_SESSION), []);

  const can = useCallback(
    (capability: Capability) => session.capabilities.includes(capability),
    [session.capabilities],
  );

  const value = useMemo<SessionContextValue>(
    () => ({
      session,
      credential,
      isConfigured: credential !== null,
      can,
      update,
      reset,
    }),
    [session, credential, can, update, reset],
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): SessionContextValue {
  const value = useContext(SessionContext);
  if (value === null) throw new Error("useSession must be used inside a SessionProvider.");
  return value;
}
