import { Container, Section } from "../../components/ui";
import { FraudPatterns } from "../../components/FraudPatterns";
import { LayerModel } from "../../components/LayerModel";

export function HowItWorks() {
  return (
    <Container>
      <Section tight>
        <div className="stack" style={{ maxWidth: "68ch" }}>
          <span className="eyebrow">How it works</span>
          <h1>Four independent layers, evaluated together</h1>
          <p className="muted">
            Each layer answers a different question, and each can pass or fail independently. A
            conclusion that something is fraudulent is only ever drawn across layers, with the
            specific evidence that supports it — never from a single layer or a single weak
            signal. Select a layer to see what it proves, and what it doesn't.
          </p>
        </div>
      </Section>

      <Section tight>
        <LayerModel />
      </Section>

      <Section tight>
        <h2>The four fraud classes Bharosa is scoped around</h2>
        <p className="muted" style={{ maxWidth: "68ch", marginTop: "var(--space-2)" }}>
          Each pattern below shows where a legitimate-looking event sequence breaks — not raw
          data, an illustration of the shape of the pattern each detector family looks for.
        </p>
        <div style={{ marginTop: "var(--space-5)" }}>
          <FraudPatterns />
        </div>
      </Section>

      <Section tight>
        <h2>Security, stated honestly</h2>
        <p className="muted" style={{ maxWidth: "68ch", marginTop: "var(--space-2)" }}>
          No layer here is unbreakable, and no claim about Bharosa should ever imply otherwise.
          A patient, low-volume attacker using a colluding retailer is a genuine residual risk
          that behavioral detection alone cannot fully close. Bharosa's honest claim is that it
          substantially raises the cost of large-scale fraud and correlates weak signals into
          strong evidence over time — never that it prevents all fraud.
        </p>
      </Section>
    </Container>
  );
}
