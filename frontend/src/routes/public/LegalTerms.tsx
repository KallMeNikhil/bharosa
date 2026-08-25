import { Container, Section } from "../../components/ui";

export function LegalTerms() {
  return (
    <Container>
      <Section tight>
        <div className="stack" style={{ maxWidth: "68ch" }}>
          <span className="eyebrow">Legal</span>
          <h1>Terms of service</h1>
          <div className="note note--info">
            Placeholder — pending legal review. This page will be replaced with the final,
            counsel-reviewed terms before public launch. Nothing on this page should be relied
            upon as a legal commitment.
          </div>
          <p className="muted">
            Bharosa does not claim regulatory or standards-body compliance — for example, GS1
            conformance or India-specific regulatory alignment — without that claim being
            separately, formally verified. No such claim is made by this page or by the product
            today.
          </p>
        </div>
      </Section>
    </Container>
  );
}
