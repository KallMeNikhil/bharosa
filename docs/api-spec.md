# Bharosa API Specification

The roadmap's M7 gate requires that no endpoint the frontend consumes exists
without first being written down here. This document is that record. The
generated OpenAPI schema at `/openapi.json` describes the same surface in
machine-readable form, but this file is the one that states intent, and it is
the one to change first when the surface changes.

Everything is served under `/api/v1`.

---

## 1. Two surfaces, two trust levels

Bharosa exposes two API surfaces that are architecturally separate and should
be thought about separately.

**The public surface** is one endpoint, `POST /verify`. Anyone can call it,
it requires no credential, and it runs against a database role
(`bharosa_verifier`) that holds SELECT on exactly two tables plus INSERT on
the verification event log. A total compromise of this surface yields no
manufacturer business data, because the credential it runs under cannot read
any.

**The internal surface** is everything else. It requires an authenticated
actor, is scoped to a single manufacturer for the life of the request, and
runs against `bharosa_app`, whose row-level security policies restrict it to
the tenant named in the request's session context.

These two surfaces never share a response shape, a database role, or an error
vocabulary.

---

## 2. Authentication, and what it is not

> **This is not authentication yet, and must not be described as such.**

The roadmap places tenant authentication and RBAC in M8. The frontend needs
authenticated, tenant-scoped endpoints before then. Rather than either
blocking the frontend or quietly building M8's authentication early, the API
resolves a credential into an actor through a `PrincipalResolver` interface
whose only current implementation reads the actor straight out of the
credential and verifies nothing.

This mirrors the signer abstraction exactly, including the factory-level
guard: requesting a resolver in a production environment raises rather than
falling back. The interface is what routes depend on, so replacing the
implementation with real authentication changes no calling code.

### Credential format

```
Authorization: Bearer dev:<manufacturer_id>:<actor_id>:<CAPABILITY,CAPABILITY>
```

`*` in the capability position grants every capability. Example:

```
Authorization: Bearer dev:3f1c...:alice:CREATE_PRODUCTION_ORDER,AUTHORIZE_SIGNING
```

### Capabilities

Issuance, signing and print authority are three separable capabilities, not
one. Holding one never implies another, and the API enforces that per route.

| Capability | Governs |
|---|---|
| `CREATE_PRODUCTION_ORDER` | Products, batches, identity reservation, activation |
| `AUTHORIZE_SIGNING` | Signing a reserved identity |
| `AUTHORIZE_PRINT` | Print, print verification, print rejection, reconciliation |
| `MANAGE_KEYS` | Key issue, rotate, revoke, mark compromised |
| `MANAGE_SUPPLY_CHAIN_REFERENCE_DATA` | Participants, territories, channel authorizations |
| `RECORD_SUPPLY_CHAIN_EVENT` | Recording custody movement |
| `RUN_DETECTION` | Running detectors |
| `REVIEW_RISK` | Producing risk assessments |
| `MANAGE_INVESTIGATION` | Opening and moving incidents |
| `RUN_SIMULATION` | Running and evaluating simulation scenarios |

---

## 3. Public verification

### `POST /verify`

Request:

```json
{
  "serial": "K4XQ...",
  "digital_link": "https://id.bharosa.example/01/09520123456788/10/B-01?bhs=K4XQ...",
  "longitude": 77.5946,
  "latitude": 12.9716,
  "reported_accuracy_m": 40,
  "channel": "WEB"
}
```

Supply either `serial` or `digital_link`. Location is optional; omitting it
degrades detection but never blocks verification, because a farmer who
declines location is not a suspect.

Response — **always this shape, in every case, including errors**:

```json
{ "state": "GENUINE", "message": "...", "checked_at": "2026-08-18T09:12:04Z" }
```

| State | Meaning |
|---|---|
| `GENUINE` | Signature valid, identity activated, no elevated evidence |
| `CAUTION` | Valid, but correlation evidence is elevated, or its signing key is compromised |
| `INVALID` | Did not verify, is not activated, or is not registered with Bharosa |
| `ALREADY_REPORTED` | An open incident already exists against this identity |
| `UNAVAILABLE` | Rate limited, or a system fault |

Three properties of this endpoint are requirements rather than
implementation details, and changing any of them is an architectural change:

1. **A single `INVALID` state covers both "did not verify" and "not
   registered".** Splitting them would confirm to an enumerator which serials
   exist. The message is worded so that genuine stock predating a
   manufacturer's onboarding is never told it is counterfeit.
2. **No response ever contains a risk score, a confidence value, a detector
   name, a location, or anything about any other identity.**
3. **Every request is held to a minimum duration**, so response timing does
   not reveal whether the code resolved.

A scan that resolves to no identity writes no row. Those scans are counted per
day and per coarse locality cell instead, so that an enumeration attack cannot
drive unbounded writes through a public endpoint.

---

## 4. Internal surface

### Identity and production

| Method | Path | Capability |
|---|---|---|
| `GET` | `/me` | any |
| `POST` | `/manufacturers` | none — non-production only |
| `POST` | `/keys` | `MANAGE_KEYS` |
| `GET` | `/keys` | any |
| `POST` | `/keys/{key_id}/rotate` | `MANAGE_KEYS` |
| `POST` | `/keys/{key_id}/revoke` | `MANAGE_KEYS` |
| `POST` | `/keys/{key_id}/compromise` | `MANAGE_KEYS` |
| `POST` | `/products` | `CREATE_PRODUCTION_ORDER` |
| `GET` | `/products` | any |
| `POST` | `/batches` | `CREATE_PRODUCTION_ORDER` |
| `GET` | `/batches` | any |
| `POST` | `/identities/reserve` | `CREATE_PRODUCTION_ORDER` |
| `POST` | `/identities/{id}/sign` | `AUTHORIZE_SIGNING` |
| `POST` | `/identities/{id}/transition` | depends on target state |
| `GET` | `/identities` | any |
| `GET` | `/identities/{id}` | any |
| `GET` | `/identities/{id}/events` | any |
| `GET` | `/identities/{id}/digital-link` | any |

Serials are never supplied by the caller. `POST /identities/reserve` takes a
`count` and generates 128-bit random serials, because a caller-chosen serial
is how sequential, guessable serials get into a system.

`/identities/{id}/digital-link` returns `409` when the product has no GTIN,
since no compliant Digital Link can be built without one.

Lifecycle transitions are `RESERVED → SIGNED → PRINTED → PRINT_VERIFIED →
RECONCILED → ACTIVATED`, with `PRINT_REJECTED` reachable from any print stage.
Only `ACTIVATED` identities verify as `GENUINE`.

### Supply chain

| Method | Path | Capability |
|---|---|---|
| `POST` | `/supply-chain/participants` | `MANAGE_SUPPLY_CHAIN_REFERENCE_DATA` |
| `GET` | `/supply-chain/participants` | any |
| `POST` | `/supply-chain/territories` | `MANAGE_SUPPLY_CHAIN_REFERENCE_DATA` |
| `GET` | `/supply-chain/territories` | any |
| `POST` | `/supply-chain/channel-authorizations` | `MANAGE_SUPPLY_CHAIN_REFERENCE_DATA` |
| `GET` | `/supply-chain/channel-authorizations` | any |
| `POST` | `/supply-chain/channel-authorizations/{id}/revoke` | `MANAGE_SUPPLY_CHAIN_REFERENCE_DATA` |
| `POST` | `/supply-chain/events` | `RECORD_SUPPLY_CHAIN_EVENT` |
| `GET` | `/supply-chain/identities/{id}/events` | any |
| `GET` | `/supply-chain/identities/{id}/custodian` | any |

Territories are real polygons, submitted as WKT `MULTIPOLYGON` in EPSG:4326
and rejected if invalid.

`RETURN` and `REALLOCATION` are ordinary event types, not exceptions.
End-of-season stock moving backwards and a distributor shifting stock between
its own retailers are normal commerce, and the frontend should present them as
such.

There is no stored current-custodian column. `/custodian` recomputes it from
the event log on every request.

### Detection, risk and investigation

| Method | Path | Capability |
|---|---|---|
| `GET` | `/identities/{id}/verification-events` | any |
| `POST` | `/identities/{id}/detection-runs` | `RUN_DETECTION` |
| `GET` | `/identities/{id}/evidence` | any |
| `POST` | `/identities/{id}/risk-assessments` | `REVIEW_RISK` |
| `GET` | `/identities/{id}/risk-assessments` | any |
| `POST` | `/investigations` | `MANAGE_INVESTIGATION` |
| `GET` | `/investigations` | any |
| `GET` | `/investigations/{id}` | any |
| `POST` | `/investigations/{id}/transitions` | `MANAGE_INVESTIGATION` |
| `GET` | `/investigations/{id}/divergence` | any |
| `GET` | `/custody-graph?identity_ids=...` | any |

`POST /investigations` requires a non-empty `evidence_ids`. An incident is the
point at which the platform asserts something about a real business, so it
cannot be created without citing what it is based on. The request is rejected
if the list is empty, and rejected again by the database at commit time.

Every risk assessment returns `contributions`, and every contribution carries
a `benign_explanation` — the innocent reading of that same signal.

> **The investigation UI must show the benign explanation next to the
> incriminating one.** It is returned on every contribution specifically so
> that this is the path of least resistance rather than something a designer
> has to remember. An investigation screen that shows only the accusatory
> reading defeats the reason the field exists.

Re-assessing appends a new assessment; it never rewrites the previous one.
Detector output is versioned, and a detector change produces new evidence
going forward rather than reinterpreting old evidence, so a case can always be
read on the terms it was decided under.

---

### Simulation

| Method | Path | Capability |
|---|---|---|
| `GET` | `/simulations/catalogue` | none (public within the internal surface) |
| `POST` | `/simulations` | `RUN_SIMULATION` |
| `GET` | `/simulations` | any |
| `GET` | `/simulations/{id}` | any |
| `GET` | `/simulations/{id}/ground-truth` | any |
| `GET` | `/simulations/{id}/evaluation` | any |
| `POST` | `/simulations/{id}/evaluation` | `RUN_SIMULATION` |

A simulation runs entirely inside the caller's own tenant, exactly like every
other domain — it is not a separate sandbox with its own tenancy model.
`POST /simulations` generates a scenario, injects the requested fraud pattern
(if any) into a minority of the generated identities, and runs the real
verification → detection → risk → investigation pipeline against it before
returning. Ground truth is recorded from what the generator deliberately did,
independently of what any detector later found, so the evaluation that comes
back is a genuine comparison rather than a detector grading its own work.

The same `(scenario_type, seed)` pair reproduces the same scenario structure
and ground truth. It does not reproduce identical cryptographic key material
— signing keys are still generated by the platform's real CSPRNG, as they
would be for any manufacturer — and the identity domain's global serial
uniqueness means two runs sharing a seed cannot coexist in the same database
at once.

`POST /simulations/{id}/evaluation` re-runs detection (idempotent — a
detector that already recorded a signal for an identity does not record it
twice) and appends a new, separately sequenced evaluation row. Nothing here
is ever recomputed in place.

---

## 5. Errors

| Status | Meaning |
|---|---|
| `400` | Domain rule violated — malformed serial, invalid geometry, cross-manufacturer reference, uncited incident |
| `401` | Missing or malformed credential |
| `403` | Authenticated actor lacks the required capability |
| `404` | Not found, **or** owned by another manufacturer |
| `409` | Illegal state transition, or a key no longer eligible for signing |

`404` deliberately covers another tenant's resources. Returning `403` there
would confirm the resource exists.

---

## 6. What the frontend must not assume

- **Client code is never a security boundary.** Every capability check shown
  here is enforced server-side. Hiding a button is a courtesy to the user, not
  a control.
- **A valid signature is not "confirmed genuine".** `GENUINE` means the
  signature verified, the identity is activated, and nothing has been flagged.
  It does not mean the physical object in hand is the one the identity was
  issued for. Copy that says "verified authentic" overstates what the platform
  knows.
- **Repeated scans are normal.** A farmer checking a pack four times is
  expected behaviour and is not a warning sign.
- **Confidence is graded, never certain.** No screen should render a risk
  assessment as a verdict.

---

## 7. Open items

These are unresolved and must not be settled by implementation:

- Rate limiting is currently per-process. A multi-instance deployment needs a
  shared store before the limit means anything.
- The physical-binding (Level 2) check has a schema slot on every verification
  event and is always `NOT_PRESENTED`. The mechanism itself is production
  hardening.
- Evidence-integrity claims require external Merkle anchoring, which does not
  exist yet. Internal hash chaining is in place on every event table, but the
  claim boundary must not get ahead of the anchoring.
