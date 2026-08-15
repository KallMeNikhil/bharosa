# Bharosa

Bharosa is a behavioral-integrity platform for physical goods. It starts with a
focused problem: detecting counterfeit and compromised agrochemical products
before they reach a farmer's field.

## The problem

A QR code or serial number on a product is easy to check but hard to trust. Once
a code exists, it can be copied. A counterfeiter doesn't need to forge the
chemistry inside a pesticide bottle if they can simply photograph the code on a
genuine one and print it onto a thousand fakes. Refilled packaging, diverted
stock sold outside its intended region, and cloned identities all pass a basic
"does this code exist" check without any trouble.

That check answers the wrong question. Existence is not authenticity.

## The approach

Bharosa starts from a different premise: a code cannot realistically be made
impossible to copy, so the system shouldn't depend on that being true. Instead,
it asks whether the *behavior* of a product identity over time is physically
plausible.

A single genuine product should be scanned in a coherent sequence of places, at
a coherent pace, through a lifecycle that makes sense — manufactured, shipped,
distributed, sold, verified. A cloned code, even with a mathematically valid
signature, tends to break that coherence. It gets scanned in two cities on the
same afternoon. It shows verification events with no matching supply-chain
history. It appears at a retailer it was never shipped to.

Bharosa combines cryptographic product identity with this kind of behavioral,
temporal, geographic, and supply-chain evidence, so that a copied identity
becomes detectable through how it's used, not just whether it's valid.

## What Bharosa is built to catch

The platform targets four fraud patterns to start:

- **Full counterfeit** — a product with no genuine origin at all, sold under a
  fabricated identity.
- **Code cloning** — a genuine code copied onto illegitimate products.
- **Refilling** — genuine packaging reused with substituted or diluted
  contents.
- **Diversion** — genuine product moved and sold outside its authorized
  market or region.

## How it works, conceptually

A physical product is issued a digital identity at the point of manufacture.
That identity accumulates a legitimate lifecycle as it moves through the
supply chain, and generates verification events as it's scanned along the
way. Bharosa analyzes that accumulated history for behavioral evidence,
producing a risk and detection outcome that can be investigated by a human
reviewer rather than treated as an automatic verdict.

```
physical product → digital identity → supply-chain lifecycle
   → verification events → behavioral analysis
   → evidence → risk/detection outcome → investigation
```

## Security philosophy

No single mechanism in Bharosa is treated as unbreakable, including the
cryptography. Security here is a layered system: controlled identity
issuance, cryptographic signing, behavioral anomaly detection, lifecycle
consistency checks, geographic and temporal evidence, and supply-chain
corroboration all contribute independently. The goal is that defeating one
layer still leaves detectable evidence in the others, and that every
detection outcome is explainable and auditable rather than a black-box score.

## Architecture

Bharosa is organized around a set of clearly bounded domains — identity,
supply chain, verification, detection, investigation, risk, simulation, and
analytics — built on a Python/FastAPI backend, a React and TypeScript
frontend, and PostgreSQL with PostGIS for geospatial reasoning about product
movement. Detailed engineering and security documentation is maintained
separately and will be published as the project matures.

```
backend/    Application, domain logic, and data layer
frontend/   Web client
infra/      Local infrastructure configuration
docs/       Product, architecture, and process documentation
.github/    Continuous integration
```

## Status

Bharosa is in its early engineering phase. The foundational architecture,
security direction, database and geospatial foundation, and the initial
identity domain — including its testing and infrastructure setup — are in
place. Verification, detection, and investigation functionality are under
active development and not yet complete.

## Vision

Agrochemicals are the deliberate starting point: authenticity and supply-chain
integrity have direct consequences for farmer trust and crop outcomes, which
makes this a domain where behavioral integrity matters and where the approach
can be proven rigorously. The longer-term direction is a stronger binding
between physical products and their digital identities, increasingly robust
behavioral detection, clearer fraud evidence for investigators, and — once the
approach is proven — applicability to other categories of physical goods
where counterfeiting and diversion cause real harm.
