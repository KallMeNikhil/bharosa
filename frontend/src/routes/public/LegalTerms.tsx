import { Container, InfoNote, Section, SectionIntro } from "../../components/ui";

export function LegalTerms() {
  return (
    <>
      <div className="page-hero">
        <Container>
          <SectionIntro level={1} eyebrow="Legal" title="Terms of service" />
        </Container>
      </div>
      <Container>
        <Section tight>
          <div className="prose">
            <InfoNote>
              Placeholder — pending legal review. This page will be replaced with the final,
              counsel-reviewed terms before public launch. Nothing on this page should be relied
              upon as a legal commitment.
            </InfoNote>
            <p className="muted">
              Bharosa does not claim regulatory or standards-body compliance — for example, GS1
              conformance or India-specific regulatory alignment — without that claim being
              separately, formally verified. No such claim is made by this page or by the product
              today.
            </p>
          </div>
        </Section>
      </Container>
    </>
  );
}
