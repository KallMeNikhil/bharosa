import { Link } from "react-router-dom";

import { Container, Section } from "../../components/ui";
import { LayerModel } from "../../components/LayerModel";
import { TrustChain } from "../../components/TrustChain";

const NOT_LIST = [
  "a QR-verification app that only checks whether a code resolves to a record",
  "a general supply-chain visibility dashboard",
  "a blockchain-traceability system",
  "an image-recognition or computer-vision counterfeit detector",
];

const FRAUD_CLASSES = [
  { label: "Full counterfeit", detail: "never legitimately issued" },
  { label: "Code cloning", detail: "one identity, many objects" },
  { label: "Refilling", detail: "genuine container, reused" },
  { label: "Diversion", detail: "outside the authorized channel" },
];

export function Home() {
  return (
    <>
      <div className="ink-band">
        <Container>
          <div className="hero">
            <span className="hero__eyebrow">Product & supply-chain integrity</span>
            <h1 className="hero__title">
              A valid code can be copied. Bharosa looks for what copying leaves behind.
            </h1>
            <p className="hero__lede">
              Bharosa gives agrochemical manufacturers a way to issue a cryptographically
              controlled identity for every pack they produce, and to tell whether that
              identity's observed history is consistent with the life of one genuine physical
              object.
            </p>
            <div className="hero__actions">
              <Link to="/verify" className="button button--primary">
                Verify a product
              </Link>
              <Link to="/how-it-works" className="button button--secondary">
                How it works
              </Link>
            </div>

            <TrustChain />
          </div>
        </Container>
      </div>

      <Section>
        <Container>
          <div className="stack" style={{ gap: "var(--space-2)", marginBottom: "var(--space-5)" }}>
            <span className="eyebrow">The problem</span>
            <h2>
              A signature proves who issued a code. It cannot prove the pack in your hand is the
              one it was issued for.
            </h2>
            <p className="muted" style={{ maxWidth: "68ch" }}>
              An attacker who obtains one genuine pack can copy its entire code, signature
              included, onto any number of counterfeit bottles. Every copy verifies as authentic
              under a system that only checks whether the code is valid. Bharosa is built around
              closing exactly that gap.
            </p>
          </div>

          <LayerModel compact />

          <div className="fraud-class-strip" aria-label="The four fraud classes Bharosa is scoped around">
            {FRAUD_CLASSES.map((item) => (
              <div className="fraud-class-strip__item" key={item.label}>
                <span className="fraud-class-strip__label">{item.label}</span>
                <span className="fraud-class-strip__detail">{item.detail}</span>
              </div>
            ))}
          </div>
        </Container>
      </Section>

      <div className="section-band">
        <Section tight>
          <Container>
            <div className="grid-2">
              <div className="stack">
                <h2>What Bharosa is not</h2>
                <ul className="not-list">
                  {NOT_LIST.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
              <div className="stack">
                <h2>What Bharosa actually claims</h2>
                <p className="muted">
                  Behavioral evidence accumulates toward a graded confidence, never a claim of
                  mathematical certainty. Every signal traces back to raw events a human can audit.
                  A cryptographically valid signature proves issuance and non-revocation only —
                  never, by itself, that the object in hand is genuine.
                </p>
              </div>
            </div>
          </Container>
        </Section>
      </div>

      <Section tight>
        <Container>
          <div className="ink-surface cta-band">
            <div>
              <span className="eyebrow" style={{ color: "var(--color-ink-accent)" }}>
                Ready when you are
              </span>
              <h2 style={{ color: "var(--color-ink-heading)", marginTop: "4px" }}>
                Have a pack in hand?
              </h2>
              <p style={{ color: "var(--color-ink-lede)", marginTop: "4px" }}>
                Check it in seconds, from an ordinary phone camera, with no app to install.
              </p>
            </div>
            <Link to="/verify" className="button button--primary">
              Verify a product
            </Link>
          </div>
        </Container>
      </Section>
    </>
  );
}
