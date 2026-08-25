import { Container, Section } from "../../components/ui";

export function Contact() {
  return (
    <Container>
      <Section tight>
        <div className="stack" style={{ maxWidth: "60ch" }}>
          <span className="eyebrow">Contact</span>
          <h1>Get in touch</h1>
          <p className="muted">
            For manufacturer onboarding, partnership, or press inquiries, reach the Bharosa team
            through your existing point of contact.
          </p>
          <div className="note note--info">
            Placeholder — a dedicated contact channel (email, form, or support desk) has not
            yet been finalized and will replace this note once available.
          </div>
        </div>
      </Section>
    </Container>
  );
}
