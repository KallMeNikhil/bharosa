/**
 * The Bharosa API, as this device talks to it.
 *
 * Unlike the consumer app, which calls one public endpoint anonymously, this
 * device is an actor inside a manufacturer's tenant and every call carries a
 * credential. Nothing here is authentication: the backend's development
 * resolver reads the actor straight out of the credential string. Real tenant
 * authentication replaces `Connection.credential` without changing any call
 * site here, which is the point of keeping it a single opaque field.
 */

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

/** The network was unreachable. Distinct from the server refusing a request. */
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
    // FastAPI returns `detail` as either a string or a list of validation
    // objects. Only the string form is worth showing to a storeman.
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

/**
 * Builds the credential the backend's development resolver expects.
 *
 * The device is issued exactly one capability. A scanner that could also mint
 * identities or rotate keys would be a far more valuable thing to steal from a
 * loading bay than one that can only say "this pack moved".
 */
export function buildCredential(manufacturerId: string, actorId: string): string {
  return `dev:${manufacturerId.trim()}:${actorId.trim()}:RECORD_SUPPLY_CHAIN_EVENT`;
}

export function whoami(connection: Connection): Promise<Actor> {
  return request<Actor>(connection, "/me");
}

export function listParticipants(connection: Connection): Promise<Participant[]> {
  return request<Participant[]>(connection, "/supply-chain/participants");
}

/**
 * Finds the identity a scanned serial belongs to.
 *
 * Resolves to null when nothing matches, which is an ordinary outcome rather
 * than an error: an unregistered code is exactly the thing this app exists to
 * surface at the loading bay.
 */
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
