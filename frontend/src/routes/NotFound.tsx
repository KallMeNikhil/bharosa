import { Link } from "react-router-dom";

import { Container, Section } from "../components/ui";

export function NotFound() {
  return (
    <Container>
      <Section>
        <div className="stack" style={{ textAlign: "center", gap: "12px" }}>
          <h1>Page not found</h1>
          <p className="muted">The page you're looking for doesn't exist.</p>
          <Link to="/" className="button button--primary" style={{ alignSelf: "center" }}>
            Back to home
          </Link>
        </div>
      </Section>
    </Container>
  );
}
