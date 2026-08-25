export const DEFAULT_BASE_URL =
  process.env.EXPO_PUBLIC_API_BASE_URL ?? "http://192.168.1.3:8000/api/v1";

const REQUEST_TIMEOUT_MS = 12_000;

export type ParticipantRole = "DEPOT" | "DISTRIBUTOR" | "RETAILER";

export interface Participant {
  id: string;
  manufacturer_id: string;
  participant_ref: string;
  name: string;
  role: ParticipantRole;
}

export interface Actor {
  actor_id: string;
  manufacturer_id: string;
  capabilities: string[];
}

export interface Identity {
  id: string;
  manufacturer_id: string;
  batch_id: string;
  serial: string;
  lifecycle_state: string;
  created_at: string;
  signed_at: string | null;
  activated_at: string | null;
}

export interface Custodian {
  identity_id: string;
  custodian_id: string | null;
}

export interface SupplyChainEventBody {
  identity_id: string;
  event_type: string;
  occurred_at: string;
  source_participant_id?: string | null;
  destination_participant_id?: string | null;
  reason?: string | null;
}

export interface SupplyChainEvent {
  id: string;
  identity_id: string;
  sequence: number;
  event_type: string;
  occurred_at: string;
}

export interface Connection {
  baseUrl: string;
  credential: string;
}

export class OfflineError extends Error {
  constructor() {
    super("Could not reach the server.");
  }
}

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(
  connection: Connection,
  path: string,
  init?: { method?: string; body?: unknown },
): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  let response: Response;
  try {
    response = await fetch(`${connection.baseUrl}${path}`, {
      method: init?.method ?? "GET",
      headers: {
        Accept: "application/json",
        Authorization: `Bearer ${connection.credential}`,
        ...(init?.body ? { "Content-Type": "application/json" } : {}),
      },
      body: init?.body ? JSON.stringify(init.body) : undefined,
      signal: controller.signal,
    });
  } catch {
    throw new OfflineError();
  } finally {
    clearTimeout(timeout);
  }

  if (!response.ok) {

    let detail = `The server refused that (${response.status}).`;
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      // A non-JSON error body tells us nothing better than the status did.
    }
    throw new ApiError(response.status, detail);
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export function buildCredential(manufacturerId: string, actorId: string): string {
  return `dev:${manufacturerId.trim()}:${actorId.trim()}:RECORD_SUPPLY_CHAIN_EVENT`;
}

export function whoami(connection: Connection): Promise<Actor> {
  return request<Actor>(connection, "/me");
}

export function listParticipants(connection: Connection): Promise<Participant[]> {
  return request<Participant[]>(connection, "/supply-chain/participants");
}

export async function resolveSerial(
  connection: Connection,
  serial: string,
): Promise<Identity | null> {
  const found = await request<Identity[]>(
    connection,
    `/identities?serial=${encodeURIComponent(serial.trim().toUpperCase())}&limit=1`,
  );
  return found[0] ?? null;
}

export function currentCustodian(
  connection: Connection,
  identityId: string,
): Promise<Custodian> {
  return request<Custodian>(
    connection,
    `/supply-chain/identities/${identityId}/custodian`,
  );
}

export function recordEvent(
  connection: Connection,
  body: SupplyChainEventBody,
): Promise<SupplyChainEvent> {
  return request<SupplyChainEvent>(connection, "/supply-chain/events", {
    method: "POST",
    body,
  });
}
