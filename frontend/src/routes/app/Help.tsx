import { Link } from "react-router-dom";

import { Container, PageHeader } from "../../components/ui";

const TERMS = [
  { term: "Lifecycle state", body: "Where a specific identity sits in its own operational lifecycle \u2014 reserved, signed, printed, activated, and so on. Not the same as its real-world location." },
  { term: "Evidence", body: "A specific, cited signal from a detector. Evidence is never a verdict on its own." },
  { term: "Risk assessment", body: "An aggregation of evidence for an identity over a time window, with an explicit confidence level." },
  { term: "Incident", body: "A human/system conclusion that always cites the evidence it rests on. Never created from a single weak signal." },
];

export function Help() {
  return (
    <Container>
      <PageHeader
        eyebrow="Workspace"
        title="Help"
        description="Quick reference for the concepts used throughout the workspace."
      />

      <div className="grid-2" style={{ marginTop: "var(--space-2)" }}>
        {TERMS.map((item) => (
          <div className="card" key={item.term}>
            <div className="card__body">
              <h3>{item.term}</h3>
              <p className="muted">{item.body}</p>
            </div>
          </div>
        ))}
      </div>

      <p className="muted" style={{ marginTop: "var(--space-5)" }}>
        For the full trust model, see <Link to="/how-it-works">How it works</Link>. For anything
        else, see <Link to="/contact">Contact</Link>.
      </p>
    </Container>
  );
}
