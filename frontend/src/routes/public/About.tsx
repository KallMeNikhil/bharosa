import { Icon } from "../../components/icons";
import type { IconName } from "../../components/icons";
import { Container, Reveal, Section, SectionIntro } from "../../components/ui";

const USERS: { role: string; body: string; icon: IconName }[] = [
  {
    role: "Agrochemical manufacturer",
    body: "The primary customer. Onboards once, then issues digital identities for its products and monitors the resulting behavioral and supply-chain signals.",
    icon: "product",
  },
  {
    role: "Farmers / field users",
    body: "Verify a product by scanning its visible code with an ordinary phone camera. No app installation required.",
    icon: "scan",
  },
  {
    role: "Distributors and retailers",
    body: "Confirm receipt and sale events, and can perform a deeper spot-check when a result looks suspicious.",
    icon: "supply",
  },
  {
    role: "Field investigators",
    body: "Review flagged incidents, correlate evidence, and determine where in the legitimate supply chain an anomaly first diverged.",
    icon: "investigate",
  },
];

export function About() {
  return (
    <>
      <div className="page-hero">
        <Container>
          <SectionIntro level={1} eyebrow="About Bharosa" title="Behavioral integrity for physical goods">
            <p>
              Bharosa is not a QR-verification app, a supply-chain dashboard, a blockchain-traceability
              system, or an image-recognition counterfeit detector. It evaluates the observed history
              and behavior of a scanned identity against what one legitimate physical product's
              lifecycle could plausibly look like.
            </p>
          </SectionIntro>
        </Container>
      </div>

      <Container>
        <Section tight>
          <Reveal>
            <SectionIntro title="Who Bharosa serves" />
          </Reveal>
          <div className="grid-2 grid-2--stretch">
            {USERS.map((user, index) => (
              <Reveal className="card card--lift role-card" key={user.role} delay={index % 2 === 0 ? 0 : 1}>
                <div className="card__body">
                  <span className="role-card__meta">
                    <span className="role-card__index">{String(index + 1).padStart(2, "0")}</span>
                    <Icon name={user.icon} size={20} />
                  </span>
                  <h3>{user.role}</h3>
                  <p className="muted">{user.body}</p>
                </div>
              </Reveal>
            ))}
          </div>
        </Section>
      </Container>
    </>
  );
}
