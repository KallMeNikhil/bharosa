import { setCredential } from "../api/client";
import { identity, intelligence, publicSurface, supplyChain } from "../api/endpoints";
import { describeError } from "../hooks/useResource";
import type { Session } from "../session/SessionContext";

export interface ScenarioLine {
  kind: "step" | "done" | "fail";
  text: string;
}

export interface DemoOutcome {
  session: Session;
  cleanIdentityId: string;
  divertedIdentityId: string;
  unactivatedIdentityId: string;
  incidentId: string | null;
}

const KARNATAKA_WKT =
  "MULTIPOLYGON(((74.0 11.5, 78.6 11.5, 78.6 18.5, 74.0 18.5, 74.0 11.5)))";

const BENGALURU = { longitude: 77.5946, latitude: 12.9716 };
const NEW_DELHI = { longitude: 77.209, latitude: 28.6139 };
const KOLKATA = { longitude: 88.3639, latitude: 22.5726 };
const MUMBAI = { longitude: 72.8777, latitude: 19.076 };

const ACTOR_ID = "demo-operator";

function isoDaysAgo(days: number): string {
  return new Date(Date.now() - days * 86_400_000).toISOString();
}

function isoDate(offsetDays: number): string {
  return new Date(Date.now() + offsetDays * 86_400_000).toISOString().slice(0, 10);
}

/**
 * Drives the documented API surface end to end so that every screen has
 * something real to show: one pack that behaves, one that is diverted and
 * scanned in four cities, and one scanned before it was ever activated.
 *
 * It calls the same endpoints a browser would, in the same order a real
 * operator would. Nothing here reaches past the API into the database.
 */
export async function runDemoScenario(
  report: (line: ScenarioLine) => void,
): Promise<DemoOutcome> {
  const step = (text: string) => report({ kind: "step", text });
  const done = (text: string) => report({ kind: "done", text });

  const suffix = new Date().toISOString().slice(11, 19).replace(/:/g, "");
  const manufacturerName = `Harit Agro Sciences ${suffix}`;

  step("Onboarding a manufacturer");
  const manufacturer = await identity.createManufacturer(manufacturerName);
  const session: Session = {
    manufacturerId: manufacturer.id,
    manufacturerName,
    actorId: ACTOR_ID,
    capabilities: [],
  };
  setCredential(`dev:${manufacturer.id}:${ACTOR_ID}:*`);
  done(`Manufacturer ${manufacturer.id}`);

  step("Issuing a signing key");
  const issued = await identity.createKey(1);
  done(`Key version ${issued.key.key_version} is ACTIVE`);

  step("Registering a product and a batch");
  const product = await identity.createProduct({
    product_ref: "URJA-500ML",
    name: "Urja 500ml systemic fungicide",
    gtin: "09520123456788",
  });
  const batch = await identity.createBatch({
    product_id: product.id,
    batch_ref: "B-2026-04",
    manufacturing_date: isoDate(-60),
    expiry_date: isoDate(670),
  });
  done(`Product ${product.product_ref}, batch ${batch.batch_ref}`);

  step("Reserving three identities");
  const reserved = await identity.reserveIdentities(batch.id, 3);
  done("Three 128-bit serials generated server-side");

  step("Signing all three");
  for (const row of reserved) {
    await identity.signIdentity(row.id, {
      manufacturer_key_id: issued.key.id,
      key_handle: issued.key_handle,
    });
  }
  done("Three identities signed");

  const [clean, diverted, unactivated] = reserved;

  step("Taking two identities through print and activation");
  for (const row of [clean, diverted]) {
    await identity.transitionIdentity(row.id, "PRINTED");
    await identity.transitionIdentity(row.id, "PRINT_VERIFIED");
    await identity.transitionIdentity(row.id, "RECONCILED");
    await identity.transitionIdentity(row.id, "ACTIVATED");
  }
  done("Two activated; the third deliberately left at SIGNED");

  step("Registering supply chain participants");
  const depot = await supplyChain.createParticipant({
    participant_ref: "DEP-BLR",
    name: "Bengaluru depot",
    role: "DEPOT",
  });
  const distributor = await supplyChain.createParticipant({
    participant_ref: "DIS-KA-01",
    name: "Karnataka distributor",
    role: "DISTRIBUTOR",
  });
  const authorizedRetailer = await supplyChain.createParticipant({
    participant_ref: "RET-MYS-01",
    name: "Mysuru agri store",
    role: "RETAILER",
  });
  const unauthorizedRetailer = await supplyChain.createParticipant({
    participant_ref: "RET-UNK-09",
    name: "Unlisted trader",
    role: "RETAILER",
  });
  done("Depot, distributor and two retailers");

  step("Defining an authorized territory");
  const territory = await supplyChain.createTerritory({
    territory_ref: "KA-SOUTH",
    name: "Southern Karnataka",
    boundary_wkt: KARNATAKA_WKT,
  });
  for (const participant of [distributor, authorizedRetailer]) {
    await supplyChain.createAuthorization({
      participant_id: participant.id,
      territory_id: territory.id,
      valid_from: isoDaysAgo(365),
    });
  }
  done("Distributor and one retailer authorized; the trader deliberately is not");

  step("Recording custody for both activated identities");
  for (const row of [clean, diverted]) {
    await supplyChain.recordEvent({
      identity_id: row.id,
      event_type: "DISPATCH",
      occurred_at: isoDaysAgo(20),
      source_participant_id: depot.id,
      destination_participant_id: distributor.id,
    });
    await supplyChain.recordEvent({
      identity_id: row.id,
      event_type: "RECEIPT",
      occurred_at: isoDaysAgo(18),
      source_participant_id: depot.id,
      destination_participant_id: distributor.id,
    });
  }

  await supplyChain.recordEvent({
    identity_id: clean.id,
    event_type: "TRANSFER",
    occurred_at: isoDaysAgo(10),
    source_participant_id: distributor.id,
    destination_participant_id: authorizedRetailer.id,
  });
  await supplyChain.recordEvent({
    identity_id: clean.id,
    event_type: "RETAIL_PLACEMENT",
    occurred_at: isoDaysAgo(8),
    source_participant_id: authorizedRetailer.id,
  });

  await supplyChain.recordEvent({
    identity_id: diverted.id,
    event_type: "TRANSFER",
    occurred_at: isoDaysAgo(9),
    source_participant_id: distributor.id,
    destination_participant_id: unauthorizedRetailer.id,
    reason: "Moved to a trader holding no channel authorization",
  });
  done("One pack follows the authorized route; the other leaves it");

  step("Scanning the well-behaved pack once, inside its territory");
  await publicSurface.verify({ serial: clean.serial, ...BENGALURU, reported_accuracy_m: 30 });
  done("Scanned in Bengaluru");

  step("Scanning the diverted pack in four cities within seconds");
  for (const place of [BENGALURU, NEW_DELHI, KOLKATA, MUMBAI]) {
    await publicSurface.verify({ serial: diverted.serial, ...place, reported_accuracy_m: 40 });
  }
  done("Four scans, three of them outside the authorized territory");

  step("Scanning a pack that was never activated");
  await publicSurface.verify({
    serial: unactivated.serial,
    ...BENGALURU,
    reported_accuracy_m: 60,
  });
  done("Answered INVALID, and still recorded a pre-activation scan");

  step("Running detection on all three identities");
  const cleanEvidence = await intelligence.runDetection(clean.id);
  await intelligence.runDetection(unactivated.id);
  const divertedEvidence = await intelligence.runDetection(diverted.id);
  done(
    `${cleanEvidence.length} signals on the clean pack, ` +
      `${divertedEvidence.length} on the diverted one`,
  );

  let incidentId: string | null = null;
  if (divertedEvidence.length > 0) {
    step("Assessing risk and opening an investigation");
    const assessment = await intelligence.assessRisk(diverted.id);
    const incident = await intelligence.openInvestigation({
      risk_assessment_id: assessment.id,
      evidence_ids: divertedEvidence.map((row) => row.id),
      summary:
        "Scanned in four cities within seconds, three of them outside the authorized " +
        "territory, after moving to a trader holding no channel authorization.",
    });
    incidentId = incident.id;
    done(`Confidence ${assessment.confidence}; incident opened`);

    step("Re-scanning the reported pack");
    const rescan = await publicSurface.verify({ serial: diverted.serial, ...BENGALURU });
    done(`Public verification now answers ${rescan.state}`);
  } else {
    report({ kind: "fail", text: "No evidence was produced, so no incident was opened." });
  }

  return {
    session,
    cleanIdentityId: clean.id,
    divertedIdentityId: diverted.id,
    unactivatedIdentityId: unactivated.id,
    incidentId,
  };
}

export function scenarioFailure(cause: unknown): ScenarioLine {
  return { kind: "fail", text: describeError(cause) };
}
