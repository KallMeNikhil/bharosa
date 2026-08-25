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
    // A non-JSON error body tells us nothing better than the status did.
  }
}

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

export async function flush(connection: Connection): Promise<FlushResult> {
  const entries = await readOutbox();
  const result: FlushResult = { sent: 0, rejected: 0, offline: false };

  for (const entry of entries) {
    for (const event of entry.events) {
      if (event.state !== "queued") continue;

      try {
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

  const remaining = entries.filter((entry) =>
    entry.events.some((event) => event.state !== "sent"),
  );
  await writeOutbox(remaining);
  return result;
}

export async function discard(entryId: string): Promise<OutboxEntry[]> {
  const remaining = (await readOutbox()).filter((entry) => entry.id !== entryId);
  await writeOutbox(remaining);
  return remaining;
}
