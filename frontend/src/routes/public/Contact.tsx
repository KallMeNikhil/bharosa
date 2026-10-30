import { Container, InfoNote, Section, SectionIntro } from "../../components/ui";

export function Contact() {
  return (
    <>
      <div className="page-hero">
        <Container>
          <SectionIntro level={1} eyebrow="Contact" title="Get in touch">
            <p>
              For manufacturer onboarding, partnership, or press inquiries, reach the Bharosa team
              through your existing point of contact.
            </p>
          </SectionIntro>
        </Container>
      </div>
      <Container>
        <Section tight>
          <div className="prose">
            <InfoNote>
              Placeholder — a dedicated contact channel (email, form, or support desk) has not
              yet been finalized and will replace this note once available.
            </InfoNote>
          </div>
        </Section>
      </Container>
    </>
  );
}
