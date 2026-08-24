import type { MovementKind, PackStatus } from "../theme";

/**
 * A consignment being built.
 *
 * This is the unit of work at a loading bay: one lorry, one shelf run, one
 * return. Packs accumulate into it while the camera stays open and nothing
 * reaches the platform until it is committed, so a half-scanned pallet that
 * gets interrupted leaves no partial record behind.
 */
export interface ScannedPack {
  serial: string;
  identityId: string | null;
  status: PackStatus;
  scannedAt: string;
}

export interface Consignment {
  id: string;
  kind: MovementKind;
  /** The participant this device belongs to. */
  selfId: string;
  counterpartyId: string | null;
  counterpartyName: string | null;
  packs: ScannedPack[];
  startedAt: string;
}

export interface Endpoints {
  sourceId: string | null;
  destinationId: string | null;
}

/**
 * Which participant sits on each end of the event, by movement.
 *
 * Receiving is the one movement where this device is the destination; in
 * every other case stock is leaving, so the device is the source. Getting
 * this backwards would invert the custody chain, so it lives in one place
 * rather than being decided at each call site.
 */
export function endpointsFor(consignment: Consignment): Endpoints {
  const { kind, selfId, counterpartyId } = consignment;
  if (kind === "RECEIPT") {
    return { sourceId: counterpartyId, destinationId: selfId };
  }
  if (kind === "RETAIL_PLACEMENT") {
    return { sourceId: selfId, destinationId: null };
  }
  return { sourceId: selfId, destinationId: counterpartyId };
}

/**
 * Who the record says should be holding a pack immediately before this
 * movement.
 *
 * Stock you are receiving should be held by whoever sent it; stock you are
 * sending should be held by you. A mismatch is not proof of anything -- a
 * depot that forgot to scan an inbound load produces the same signal as a
 * diverted pack -- so this only ever raises a flag for a human.
 */
export function expectedHolderFor(consignment: Consignment): string | null {
  return consignment.kind === "RECEIPT"
    ? consignment.counterpartyId
    : consignment.selfId;
}

export function statusFor(
  consignment: Consignment,
  custodianId: string | null,
): PackStatus {
  const expected = expectedHolderFor(consignment);
  if (custodianId === expected) return "known";
  // A pack with no custodian has never left the plant. Receiving one straight
  // from the manufacturer is ordinary; sending one you never received is not.
  if (custodianId === null && consignment.kind === "RECEIPT") return "known";
  return "held";
}

export function newConsignment(
  kind: MovementKind,
  selfId: string,
  counterparty: { id: string; name: string } | null,
): Consignment {
  return {
    id: `${Date.now()}`,
    kind,
    selfId,
    counterpartyId: counterparty?.id ?? null,
    counterpartyName: counterparty?.name ?? null,
    packs: [],
    startedAt: new Date().toISOString(),
  };
}

export function containsSerial(consignment: Consignment, serial: string): boolean {
  return consignment.packs.some((pack) => pack.serial === serial);
}

export function countByStatus(packs: ScannedPack[]): Record<PackStatus, number> {
  const counts: Record<PackStatus, number> = {
    known: 0,
    held: 0,
    unknown: 0,
    pending: 0,
  };
  for (const pack of packs) counts[pack.status] += 1;
  return counts;
}
