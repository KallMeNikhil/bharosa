import AsyncStorage from "@react-native-async-storage/async-storage";

import {
  ApiError,
  OfflineError,
  recordEvent,
  resolveSerial,
  type Connection,
} from "../api/client";
import { endpointsFor, type Consignment } from "./consignment";
import type { MovementKind } from "../theme";

const STORAGE_KEY = "bharosa.distributor.outbox";

/**
 * Movements recorded on the device but not yet accepted by the platform.
 *
 * A depot is the worst signal environment in the chain: a metal shed, often
 * underground, frequently at the edge of a village cell. An app that required
 * connectivity to record a movement would simply not be used, and the events
 * it failed to capture are exactly the ones the detection layer needs. So the
 * device is the system of record until the platform acknowledges each event,
 * and nothing is dropped in between.
 *
 * The queue is per-event rather than per-consignment because acceptance is
 * per-event: a lorry with one unregistered pack in it must still deliver the
 * other thirty-nine.
 */
export type PendingState = "queued" | "sent" | "rejected";

export interface PendingEvent {
  serial: string;
  identityId: string | null;
  state: PendingState;
  error?: string;
}

export interface OutboxEntry {
  id: string;
  kind: MovementKind;
  counterpartyName: string | null;
  sourceId: string | null;
  destinationId: string | null;
  occurredAt: string;
  events: PendingEvent[];
}

export interface FlushResult {
  sent: number;
  rejected: number;
  /** True when the run stopped early because the network went away. */
  offline: boolean;
}

export async function readOutbox(): Promise<OutboxEntry[]> {
  try {
    const raw = await AsyncStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as OutboxEntry[]) : [];
  } catch {
    return [];
  }
}

async function writeOutbox(entries: OutboxEntry[]): Promise<void> {
  try {
    await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(entries));
  } catch {
    // Nothing better to do here. Losing the write would lose a shift's work,
    // so the in-memory copy the caller holds stays authoritative until the
    // next successful save.
  }
}

/** Turns a finished consignment into queued events and stores them. */
export async function enqueue(consignment: Consignment): Promise<OutboxEntry> {
  const { sourceId, destinationId } = endpointsFor(consignment);
  const entry: OutboxEntry = {
    id: consignment.id,
    kind: consignment.kind,
    counterpartyName: consignment.counterpartyName,
    sourceId,
    destinationId,
    occurredAt: new Date().toISOString(),
    events: consignment.packs.map((pack) => ({
      serial: pack.serial,
      identityId: pack.identityId,
      state: "queued" as const,
    })),
  };

  await writeOutbox([entry, ...(await readOutbox())]);
  return entry;
}

export function pendingCount(entries: OutboxEntry[]): number {
  return entries.reduce(
    (total, entry) =>
      total + entry.events.filter((event) => event.state === "queued").length,
    0,
  );
}

export function rejectedCount(entries: OutboxEntry[]): number {
  return entries.reduce(
    (total, entry) =>
      total + entry.events.filter((event) => event.state === "rejected").length,
    0,
  );
}

/**
 * Sends everything still queued.
 *
 * Stops at the first network failure rather than grinding through the rest of
 * the queue, because if one request could not reach the server the next forty
 * will not either, and each one costs a twelve second timeout. A rejection is
 * different: the server was reached and refused this specific event, so the
 * run continues and the event is marked with the reason.
 */
export async function flush(connection: Connection): Promise<FlushResult> {
  const entries = await readOutbox();
  const result: FlushResult = { sent: 0, rejected: 0, offline: false };

  for (const entry of entries) {
    for (const event of entry.events) {
      if (event.state !== "queued") continue;

      try {
        // A pack scanned while offline was never resolved, so the lookup that
        // could not happen at the bay happens now, immediately before the
        // event that depends on it.
        if (!event.identityId) {
          const identity = await resolveSerial(connection, event.serial);
          if (!identity) {
            event.state = "rejected";
            event.error = "No pack with this code is registered.";
            result.rejected += 1;
            continue;
          }
          event.identityId = identity.id;
        }

        await recordEvent(connection, {
          identity_id: event.identityId,
          event_type: entry.kind,
          occurred_at: entry.occurredAt,
          source_participant_id: entry.sourceId,
          destination_participant_id: entry.destinationId,
        });
        event.state = "sent";
        result.sent += 1;
      } catch (cause) {
        if (cause instanceof OfflineError) {
          result.offline = true;
          await writeOutbox(entries);
          return result;
        }
        event.state = "rejected";
        event.error =
          cause instanceof ApiError ? cause.message : "The server refused this.";
        result.rejected += 1;
      }
    }
  }

  // An entry every event of which was accepted has served its purpose; one
  // holding a rejection stays until a person has seen it.
  const remaining = entries.filter((entry) =>
    entry.events.some((event) => event.state !== "sent"),
  );
  await writeOutbox(remaining);
  return result;
}

/** Drops one entry, rejections included. Only ever called from the outbox screen. */
export async function discard(entryId: string): Promise<OutboxEntry[]> {
  const remaining = (await readOutbox()).filter((entry) => entry.id !== entryId);
  await writeOutbox(remaining);
  return remaining;
}
