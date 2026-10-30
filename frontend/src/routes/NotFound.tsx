import { Link } from "react-router-dom";

import { Container } from "../components/ui";

export function NotFound() {
  return (
    <Container>
      <div className="not-found">
        <span className="not-found__code" aria-hidden="true">
          404
        </span>
        <h1>Page not found</h1>
        <p className="muted">The page you're looking for doesn't exist.</p>
        <Link to="/" className="button button--primary">
          Back to home
        </Link>
      </div>
    </Container>
  );
}
