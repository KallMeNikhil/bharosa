import { Container, Section } from "../../components/ui";

const USERS = [
  {
    role: "Agrochemical manufacturer",
    body: "The primary customer. Onboards once, then issues digital identities for its products and monitors the resulting behavioral and supply-chain signals.",
  },
  {
    role: "Farmers / field users",
    body: "Verify a product by scanning its visible code with an ordinary phone camera. No app installation required.",
  },
  {
    role: "Distributors and retailers",
    body: "Confirm receipt and sale events, and can perform a deeper spot-check when a result looks suspicious.",
  },
  {
    role: "Field investigators",
    body: "Review flagged incidents, correlate evidence, and determine where in the legitimate supply chain an anomaly first diverged.",
  },
];

export function About() {
  return (
    <Container>
      <Section tight>
        <div className="stack" style={{ maxWidth: "68ch" }}>
          <span className="eyebrow">About Bharosa</span>
          <h1>Behavioral integrity for physical goods</h1>
          <p className="muted">
            Bharosa is not a QR-verification app, a supply-chain dashboard, a blockchain-traceability
            system, or an image-recognition counterfeit detector. It evaluates the observed history
            and behavior of a scanned identity against what one legitimate physical product's
            lifecycle could plausibly look like.
          </p>
        </div>
      </Section>

      <Section tight>
        <h2>Who Bharosa serves</h2>
        <div className="grid-2" style={{ marginTop: "var(--space-5)" }}>
          {USERS.map((user) => (
            <div className="card" key={user.role}>
              <div className="card__body">
                <h3>{user.role}</h3>
                <p className="muted">{user.body}</p>
              </div>
            </div>
          ))}
        </div>
      </Section>
    </Container>
  );
}
