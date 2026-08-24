# Bharosa — technical reference

Everything an engineer needs to understand how this platform is put together,
what it currently does, and — just as importantly — what it does not do yet.

For getting it running, see
[`how_to_setup_on_docker.md`](how_to_setup_on_docker.md). For the exact request
and response shapes, see [`api-spec.md`](api-spec.md).

---

## 1. The premise

A code printed on a bottle can always be copied. A counterfeiter does not need
to reproduce the chemistry inside a pesticide container if they can photograph
the QR code on a genuine one and print it onto a thousand fakes.

So the platform does not ask *does this code exist*. Existence is not
authenticity, and any system whose security rests on a code being
uncopyable has already lost.

Bharosa asks a different question: **is the behaviour of this identity over
time physically plausible?** A single genuine pack is scanned in a coherent
sequence of places, at a coherent pace, through a lifecycle that makes sense.
A cloned code — even one carrying a mathematically valid signature — tends to
break that coherence. It appears in two cities on the same afternoon. It shows
verification events with no matching custody history. It surfaces at a retailer
it was never shipped to.

That reframing is the whole design. Everything below serves it.

---

## 2. System shape

```
                       ┌──────────────────────────┐
   manufacturer  ───▶  │  Web console (React)     │──┐
                       └──────────────────────────┘  │
                       ┌──────────────────────────┐  │
   farmer        ───▶  │  Consumer app (Expo)     │──┤
                       └──────────────────────────┘  │   HTTP
                       ┌──────────────────────────┐  │
   depot / retail ──▶  │  Distributor app (Expo)  │──┤
                       └──────────────────────────┘  │
                                                     ▼
                              ┌────────────────────────────────┐
                              │  FastAPI backend               │
                              │  identity · supply_chain ·     │
                              │  verification · detection ·    │
                              │  risk · investigation ·        │
                              │  simulation                    │
                              └────────────────────────────────┘
                                             │
                              ┌────────────────────────────────┐
                              │  PostgreSQL 16 + PostGIS       │
                              │  RLS · append-only event logs  │
                              └────────────────────────────────┘
```

The data flow the platform is built around:

```
physical pack → digital identity → custody lifecycle
   → verification events → detection signals
   → correlated evidence → risk outcome → investigation
```

---

## 3. Repository layout

| Path | What lives there |
| --- | --- |
| `backend/app/domains/` | All business logic, one package per bounded domain |
| `backend/app/api/v1/` | HTTP routing only — thin, no domain logic |
| `backend/app/core/` | Cross-cutting: config, database, authorization, tenancy, event chaining, signing |
| `backend/alembic/versions/` | 13 migrations; **all** grants and RLS policies live here |
| `backend/tests/` | 42 test modules |
| `frontend/` | Manufacturer web console (React + TypeScript + Vite) |
| `consumer_app/` | Farmer-facing verification app (Expo / React Native) |
| `distributor_app/` | Custody scanner for depots, distributors, retailers |
| `infra/` | Compose stack and database provisioning SQL |

Approximate size:

| Area | Files | Lines |
| --- | ---: | ---: |
| `backend/app` | 69 | 8,787 |
| `backend/tests` | 50 | 6,313 |
| `frontend/src` | 30 | 4,566 |
| `distributor_app/src` | 21 | 3,670 |
| `consumer_app/src` | 14 | 1,996 |

---

## 4. Backend architecture

Seven bounded domains. Each owns its models, its service functions and its
invariants; the API layer routes and nothing more.

| Domain | Responsibility |
| --- | --- |
| `identity` | Manufacturers, keys, products, batches, pack identities, signing, lifecycle |
| `supply_chain` | Participants, territories, channel authorizations, custody events |
| `verification` | The public scan endpoint and its event log |
| `detection` | Four detectors turning history into typed signals |
| `risk` | Likelihood-ratio correlation of signals into one outcome |
| `investigation` | Human review workflow over detected identities |
| `simulation` | Deterministic scenario generation and detector evaluation |

A test (`test_architecture_boundaries.py`) walks the AST of every domain
module and fails on any import that reaches into another domain's internals.
The layering is therefore a checked property, not a convention people have to
remember.

---

## 5. Data integrity

Three mechanisms, each doing a distinct job.

### Append-only event logs with hash chaining

Every event table — identity issuance, supply-chain custody, verification,
evidence — is append-only. `UPDATE` and `DELETE` are revoked from the
application role in the migrations themselves, so it is not a rule the code
politely follows.

Each event carries a `sequence` and an `event_hash` computed over the previous
event's hash plus its own canonical fields (`app/core/event_chain.py`). Tampering
with an event breaks every hash after it. The chain is scoped per identity, so
each pack has its own tamper-evident history.

### Row-level security, fail-closed

Tenant isolation is enforced in PostgreSQL, not in application code. Every
tenant-scoped table has an RLS policy keyed on a transaction-local setting:

```
bharosa.manufacturer_id
```

set via `set_config(..., true)` — the `true` makes it transaction-local, which
is why routes commit exactly once, at the end. A request that never sets the
setting sees **nothing**, rather than everything. Forgetting the tenant scope
is an empty result set, not a cross-tenant leak.

### Three database roles

| Role | Purpose |
| --- | --- |
| `bharosa_owner` | Owns every table, runs migrations. Never used at runtime. |
| `bharosa_app` | Tenant-scoped runtime role. Owns nothing, so it cannot `ALTER` or `DROP`. Holds no `GRANT OPTION`, so it cannot widen its own privileges. |
| `bharosa_verifier` | Public verification only. Deliberately separate because verification is inherently cross-tenant — a scanned code does not name its manufacturer until the serial resolves. Rather than weaken `bharosa_app`'s isolation, the public path runs as a role with no privilege on manufacturer business data at all. |

`bharosa_owner` is never granted to `bharosa_app`, so a compromised runtime
credential cannot escalate through `SET ROLE`.

---

## 6. Identity and lifecycle

A pack identity moves through a fixed state machine with no shortcuts:

```
RESERVED → SIGNED → PRINTED → PRINT_VERIFIED → RECONCILED → ACTIVATED
                        └────────────────┴──────────────┴──▶ PRINT_REJECTED
```

Illegal transitions raise rather than silently coerce. Each state exists
because it corresponds to a control someone signs off on in a real production
line.

Signing uses Ed25519 over a canonical payload (BHIP1). Key handles are returned
**once**, at issue or rotation, and never again — so anything that needs to sign
must hold a handle it was given, not one it can look up.

Pack codes are published as GS1 Digital Links. The serial travels in a `bhs`
extension parameter because it is longer than GS1's own serial component
permits:

```
https://id.bharosa.example/01/09520123456788/10/BATCH-REF?bhs=<26-char-serial>
```

---

## 7. Supply chain and custody

Participants are `DEPOT`, `DISTRIBUTOR` or `RETAILER`. Territories are PostGIS
multipolygons; channel authorizations bind a participant to a territory for a
validity window.

Seven custody event types: `DISPATCH`, `RECEIPT`, `TRANSFER`, `RETURN`,
`REALLOCATION`, `RETAIL_PLACEMENT`, `CUSTODY_ADJUSTMENT`.

**There is no stored custodian column.** The current custodian is re-derived
from the event log on every request, so the projection cannot drift away from
the events it summarises. Custody is whatever the last handover event says it
is.

Note that recording is deliberately permissive: the platform accepts a movement
that contradicts the recorded custodian, flags it, and lets detection decide. A
depot that forgot to scan an inbound load produces the same signal as a diverted
pack, and only the accumulated picture separates them.

---

## 8. Public verification

`POST /verify` is the one unauthenticated endpoint. It answers with a fixed
shape in every case:

| State | Meaning |
| --- | --- |
| `GENUINE` | Registered, nothing unusual in recent history |
| `CAUTION` | Needs a closer look before use |
| `INVALID` | Could not be confirmed |
| `ALREADY_REPORTED` | Already raised with the manufacturer |
| `UNAVAILABLE` | Could not be checked right now |

Two deliberate properties:

- **Constant response shape.** Every reply carries the same fields, so the
  shape reveals nothing about whether a code resolved.
- **Minimum response duration.** Every request is held to a floor
  (`verification_min_response_seconds`), so *timing* reveals nothing either.

Client identity is reduced to a salted hash (`client_reference_hash`) rather
than stored. Rate limiting is an in-process token bucket — adequate for a
single instance, and one of the things that must change before production.

---

## 9. Detection

Ten typed signals, mapped to four fraud families:

| Family | Signals |
| --- | --- |
| `FULL_COUNTERFEIT` | `SIGNATURE_INVALID`, `UNTRUSTED_KEY_AT_SCAN`, `PRE_ACTIVATION_SCAN` |
| `CODE_CLONING` | `IMPOSSIBLE_TRAVEL`, `GEOGRAPHIC_SPREAD`, `SCAN_VELOCITY` |
| `REFILLING` | `POST_SALE_SCAN_RESURGENCE`, `DORMANCY_REACTIVATION` |
| `DIVERSION` | `TERRITORY_VIOLATION`, `CHANNEL_VIOLATION` |

One detector per family (`app/domains/detection/detectors/`). Each emits
evidence carrying its detector id, version, signal type, a log-likelihood
ratio, and the source event ids it was derived from — so any piece of evidence
can be traced back to the exact events that produced it.

---

## 10. Risk correlation

Signals accumulate in **log-odds space**, where combining independent evidence
is addition. Each detector reports how many times more likely its observation
is under fraud than under legitimate use, as a natural log — which is why
detectors emit logs in the first place.

Straight addition would let a pile of weak, mutually dependent signals from one
family out-argue a single strong signal from another. So signals *within* a
family are discounted geometrically — the strongest counts in full, the next
for half of that, and so on — while families are summed without discount, since
a geographic signal and a lifecycle signal are far closer to independent than
two geographic signals are.

Every contribution carries a **benign explanation** alongside the
incriminating reading, and the console shows both side by side. A phone with
poor GPS produces the same coordinates as a cloned pack, and an interface that
displayed only the damning reading would be quietly arguing a case rather than
presenting evidence.

The prior, the discount factor and the confidence bands are **calibration
parameters, not architecture**. None of them are settled.

---

## 11. Investigation

Detected identities enter a review workflow with its own state machine and
divergence tracking (`app/domains/investigation/`). The design intent is that
detection produces evidence for a human, never an automatic verdict — the
platform never blocks a sale on its own.

---

## 12. Simulation and evaluation

Deterministic scenario generation with seeded RNG (`app/domains/simulation/`).
Injections exist for each fraud family — `inject_full_counterfeit`,
`inject_code_cloning`, `inject_refilling`, `inject_diversion`,
`inject_combined` — plus legitimate baseline traffic.

Because each generated identity carries ground truth, the evaluator computes
precision, recall and detection rate against known answers. That is what makes
detector tuning measurable rather than anecdotal.

---

## 13. Authorization

Ten capabilities, deliberately separable:

```
CREATE_PRODUCTION_ORDER   AUTHORIZE_SIGNING   AUTHORIZE_PRINT
MANAGE_KEYS               RUN_DETECTION       REVIEW_RISK
MANAGE_INVESTIGATION      RUN_SIMULATION
MANAGE_SUPPLY_CHAIN_REFERENCE_DATA
RECORD_SUPPLY_CHAIN_EVENT
```

Holding one never implies another. Issuing identities, authorising signing and
authorising print are separate powers because in a real plant they belong to
different people. The distributor scanner, for instance, holds exactly one:
`RECORD_SUPPLY_CHAIN_EVENT`. A scanner stolen from a loading bay is worth no
more than the movements it can fabricate.

### ⚠ There is no authentication

`DevelopmentOnlyPrincipalResolver` reads the actor **straight out of the
credential string**:

```
dev:<manufacturer_id>:<actor_id>:<CAPABILITY,CAPABILITY>
```

This is not weak authentication. It is a stand-in that exists so the API
surface and the clients could be built against a real actor and a real tenant
scope before authentication itself is built. A factory-level guard makes it
unreachable outside `development` and `test`; requesting it in any other
environment raises rather than falling through.

**Anyone who can reach the API can claim to be any actor in any tenant.** Do not
expose this build to an untrusted network.

---

## 14. API surface

49 endpoints under `/api/v1` (27 `GET`, 22 `POST`), excluding FastAPI's own
documentation routes:

| Group | Count |
| --- | ---: |
| `identities` | 12 |
| `supply-chain` | 10 |
| `simulations` | 7 |
| `keys` | 5 |
| `investigations` | 5 |
| `products`, `batches` | 4 |
| `health`, `ready`, `verify`, `me`, `manufacturers`, `custody-graph` | 6 |

Interactive documentation is at `/docs` while the server runs.
[`api-spec.md`](api-spec.md) is the authority the web console is written
against.

---

## 15. The clients

### Web console — `frontend/`

React 18 + TypeScript + Vite, hand-written CSS, no component library.
Fourteen route modules covering every area of the platform. Vite proxies `/api` to the backend, so the
browser makes same-origin requests and the backend needs no CORS middleware.

Every request is recorded in an in-app **API console** showing the exact body
sent and returned — the console doubles as the tool for exercising the backend
by hand.

### Consumer app — `consumer_app/`

Expo SDK 54 / React Native. Calls one public endpoint and needs no credential.

Built around a single verdict word readable at arm's length in direct sun.
Every state carries its own silhouette as well as its own colour, so the answer
survives a colour-blind reader and a washed-out screen. Scan history stays on
the device and is never uploaded.

### Distributor app — `distributor_app/`

Expo SDK 54 / React Native. The custody scanner. Without it the correlation
engine has no movement data, so diversion and refill detection run on nothing.

Modelled on a delivery challan: packs accumulate into a consignment while the
camera stays open, a numbered tally rail records each scan, and one commit
writes the lot. **Offline is the primary case, not a fallback** — a depot is
the worst signal environment in the chain, and an app that required
connectivity would simply not be used, losing exactly the events detection
depends on. The outbox queues per event rather than per consignment, because
acceptance is per event: one unregistered pack must not block the other
thirty-nine.

Both apps are pinned to **Expo SDK 54**, which is what the Play Store build of
Expo Go supports. Later SDKs will not open in it.

---

## 16. Testing

42 test modules covering domain logic, API flow, architecture boundaries, and
database privilege enforcement.

Tests marked `db_privilege` require a **real PostgreSQL with migrations
applied** — RLS policies and grants exist only in the migrations, so the
fixtures deliberately refuse to create tables themselves. A schema built any
other way would not be the schema being tested.

CI runs lint and the suite against PostGIS 16-3.4 on every push and pull
request.

```bash
docker compose -f infra/docker-compose.yml exec api pytest
```

---

## 17. What is and is not built

Built: cryptographic identity, custody log, public verification, four
fraud-family detectors, likelihood-ratio correlation, investigation workflow,
deterministic simulation and evaluation, and three clients.

**Not built, and not claimed:**

| Gap | Consequence |
| --- | --- |
| Tenant authentication | The dev principal resolver is not authentication |
| KMS / HSM signing | Keys are handled in software |
| Physical binding | Nothing ties a digital identity to a specific physical object beyond a printed code |
| External evidence anchoring | Hash chains are tamper-evident within this database only |
| Distributed rate limiting | The token bucket is per process |

Bharosa operates at whatever assurance level has actually been implemented,
never one implied by its design. Today that is **Level 1 (cryptographic
identity)** plus behavioural evidence collection. No evidence-integrity or
physical-authenticity claim should be made on the platform's behalf yet.

---

## 18. Open decisions

Two choices are implemented but not yet ratified in the architecture document:

1. **`bhs=` as the Digital Link serial parameter.** Chosen because Bharosa
   serials exceed the length GS1's own serial component allows. Works, but is
   an extension rather than a standard usage.
2. **`Capability` and `ActorContext` living in `app/core`.** They began inside
   the identity domain and were promoted when other domains needed them.

Both are worth a deliberate decision rather than inheritance by default.
