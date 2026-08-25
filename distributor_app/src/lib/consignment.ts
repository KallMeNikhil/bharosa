import type { MovementKind, PackStatus } from "../theme";

export interface ScannedPack {
  serial: string;
  identityId: string | null;
  status: PackStatus;
  scannedAt: string;
}

export interface Consignment {
  id: string;
  kind: MovementKind;
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
