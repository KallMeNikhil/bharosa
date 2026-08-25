import { Container, Section } from "../../components/ui";

export function LegalPrivacy() {
  return (
    <Container>
      <Section tight>
        <div className="stack" style={{ maxWidth: "68ch" }}>
          <span className="eyebrow">Legal</span>
          <h1>Privacy policy</h1>
          <div className="note note--info">
            Placeholder — pending legal review. This page will be replaced with the final,
            counsel-reviewed policy text before public launch. Nothing on this page should be
            relied upon as a legal commitment.
          </div>
          <p className="muted">
            Bharosa's engineering principles collect the minimum personal data needed for a scan
            event to function as a fraud signal, and never collect a name or phone number by
            default. Precise location is retained only as long as needed for detection, then
            aggregated. Exact retention windows, consent-flow copy, and the allocation of Data
            Fiduciary responsibility under India's DPDPA are legal decisions that require current
            regulatory review and are not settled by this page.
          </p>
        </div>
      </Section>
    </Container>
  );
}
