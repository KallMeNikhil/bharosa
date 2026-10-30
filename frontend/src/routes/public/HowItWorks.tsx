import { Container, Reveal, Section, SectionIntro } from "../../components/ui";
import { FraudPatterns } from "../../components/FraudPatterns";
import { LayerModel } from "../../components/LayerModel";

export function HowItWorks() {
  return (
    <>
      <div className="page-hero">
        <Container>
          <SectionIntro level={1} eyebrow="How it works" title="Four independent layers, evaluated together">
            <p>
              Each layer answers a different question, and each can pass or fail independently. A
              conclusion that something is fraudulent is only ever drawn across layers, with the
              specific evidence that supports it — never from a single layer or a single weak
              signal. Select a layer to see what it proves, and what it doesn't.
            </p>
          </SectionIntro>
        </Container>
      </div>

      <Container>
        <Section tight>
          <Reveal>
            <LayerModel />
          </Reveal>
        </Section>
      </Container>

      <div className="tint-band">
        <Container>
          <Section tight>
            <Reveal>
              <SectionIntro title="The four fraud classes Bharosa is scoped around">
                <p>
                  Each pattern below shows where a legitimate-looking event sequence breaks — not raw
                  data, an illustration of the shape of the pattern each detector family looks for.
                </p>
              </SectionIntro>
            </Reveal>
            <FraudPatterns />
          </Section>
        </Container>
      </div>

      <Container>
        <Section tight>
          <Reveal className="honesty">
            <div className="honesty__body">
              <h2>Security, stated honestly</h2>
              <p>
                No layer here is unbreakable, and no claim about Bharosa should ever imply otherwise.
                A patient, low-volume attacker using a colluding retailer is a genuine residual risk
                that behavioral detection alone cannot fully close. Bharosa's honest claim is that it
                substantially raises the cost of large-scale fraud and correlates weak signals into
                strong evidence over time — never that it prevents all fraud.
              </p>
            </div>
          </Reveal>
        </Section>
      </Container>
    </>
  );
}
