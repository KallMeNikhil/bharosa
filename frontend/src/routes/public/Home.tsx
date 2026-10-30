import type { CSSProperties } from "react";
import { Link } from "react-router-dom";

import { Icon } from "../../components/icons";
import { LayerModel } from "../../components/LayerModel";
import { CodeField } from "../../components/CodeField";
import { TrustChain } from "../../components/TrustChain";
import { Container, Reveal, Section, SectionIntro } from "../../components/ui";

const NOT_LIST = [
  "a QR-verification app that checks whether a code resolves to a record",
  "a general supply-chain visibility dashboard",
  "a blockchain-traceability system",
  "an image-recognition or computer-vision counterfeit detector",
];

type Step = "ok" | "break" | "flag";

const FRAUD_CLASSES: { label: string; detail: string; steps: Step[] }[] = [
  { label: "Full counterfeit", detail: "never legitimately issued", steps: ["flag", "break", "break"] },
  { label: "Code cloning", detail: "one identity, many objects", steps: ["ok", "ok", "break", "flag"] },
  { label: "Refilling", detail: "genuine container, reused", steps: ["ok", "ok", "ok", "break", "flag"] },
  { label: "Diversion", detail: "outside the authorized channel", steps: ["ok", "ok", "break", "flag"] },
];

export function Home() {
  return (
    <>
      <div className="ink-band hero-band">
        <CodeField className="hero-band__field" />
        <div className="hero-band__scrim" aria-hidden="true" />
        <Container>
          <div className="hero">
            <div className="hero__copy">
              <span className="hero__label">Product & supply-chain integrity</span>
              <h1 className="hero__title">
                A valid code can be copied.{" "}
                <span className="hero__title-accent">Bharosa looks for what copying leaves behind.</span>
              </h1>
              <p className="hero__lede">
                Bharosa gives agrochemical manufacturers a way to issue a cryptographically
                controlled identity for every pack they produce, and to tell whether that
                identity's observed history is consistent with the life of one genuine physical
                object.
              </p>
              <div className="hero__actions">
                <Link to="/verify" className="button button--primary button--lg">
                  Verify a product
                  <span className="icon--nudge">
                    <Icon name="arrow" size={18} />
                  </span>
                </Link>
                <Link to="/how-it-works" className="button button--secondary button--lg">
                  How it works
                </Link>
              </div>
            </div>
          </div>

          <TrustChain />
        </Container>
      </div>

      <Section>
        <Container>
          <Reveal>
            <SectionIntro
              eyebrow="The problem"
              title="A signature proves who issued a code. It cannot prove the pack in your hand is the one it was issued for."
            >
              <p>
                An attacker who obtains one genuine pack can copy its entire code, signature
                included, onto any number of counterfeit bottles. Every copy verifies as authentic
                under a system that only checks whether the code is valid. Bharosa is built around
                closing exactly that gap.
              </p>
            </SectionIntro>
          </Reveal>

          <Reveal delay={1}>
            <LayerModel compact />
          </Reveal>

          <Reveal delay={1}>
            <ol className="fraud-class-strip" aria-label="The four fraud classes Bharosa is scoped around">
              {FRAUD_CLASSES.map((item, index) => (
                <li key={item.label}>
                  <Link to="/how-it-works" className="fraud-class-strip__item">
                    <span className="fraud-class-strip__index">{String(index + 1).padStart(2, "0")}</span>
                    <span className="fraud-class-strip__label">{item.label}</span>
                    <span className="fraud-class-strip__detail">{item.detail}</span>
                    <span className="mini-seq" aria-hidden="true">
                      {item.steps.map((step, stepIndex) => (
                        <span
                          key={stepIndex}
                          className={`mini-seq__dot mini-seq__dot--${step}`}
                          style={{ "--i": stepIndex } as CSSProperties}
                        />
                      ))}
                    </span>
                  </Link>
                </li>
              ))}
            </ol>
          </Reveal>
        </Container>
      </Section>

      <div className="section-band">
        <Section tight>
          <Container>
            <div className="claims">
              <Reveal className="claims__col claims__col--not">
                <h2>What Bharosa is not</h2>
                <ul className="not-list">
                  {NOT_LIST.map((item) => (
                    <li key={item}>
                      <span className="not-list__mark" aria-hidden="true">
                        <Icon name="cross" size={14} />
                      </span>
                      {item}
                    </li>
                  ))}
                </ul>
              </Reveal>
              <Reveal className="claims__col claims__col--is" delay={1}>
                <h2>What Bharosa actually claims</h2>
                <p className="claims__quote">
                  Behavioral evidence accumulates toward a graded confidence, never a claim of
                  mathematical certainty. Every signal traces back to raw events a human can audit.
                  A cryptographically valid signature proves issuance and non-revocation only —
                  never, by itself, that the object in hand is genuine.
                </p>
              </Reveal>
            </div>
          </Container>
        </Section>
      </div>

      <Section tight>
        <Container>
          <Reveal className="ink-surface cta-band">
            <div className="cta-band__copy">
              <span className="eyebrow">Ready when you are</span>
              <h2>Have a pack in hand?</h2>
              <p>Check it in seconds, from an ordinary phone camera, with no app to install.</p>
            </div>
            <Link to="/verify" className="button button--primary button--lg">
              Verify a product
              <span className="icon--nudge">
                <Icon name="arrow" size={18} />
              </span>
            </Link>
          </Reveal>
        </Container>
      </Section>
    </>
  );
}
