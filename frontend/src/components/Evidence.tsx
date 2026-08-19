import type { ContributionView, EvidenceView, RiskAssessmentView } from "../api/types";
import { Badge, Empty, Timestamp } from "./ui";

export function contributionsByEvidence(
  assessment: RiskAssessmentView | null | undefined,
): Map<string, ContributionView> {
  const index = new Map<string, ContributionView>();
  for (const contribution of assessment?.contributions ?? []) {
    index.set(contribution.evidence_id, contribution);
  }
  return index;
}

export function EvidenceList({
  evidence,
  contributions,
  selectable,
  selected,
  onToggle,
}: {
  evidence: EvidenceView[];
  contributions?: Map<string, ContributionView>;
  selectable?: boolean;
  selected?: string[];
  onToggle?: (evidenceId: string) => void;
}) {
  if (evidence.length === 0) {
    return <Empty>No evidence has been recorded for this identity.</Empty>;
  }

  return (
    <>
      {evidence.map((item) => {
        const contribution = contributions?.get(item.id);
        return (
          <article key={item.id} className="evidence">
            <header className="evidence__head">
              {selectable && (
                <input
                  type="checkbox"
                  style={{ width: "auto" }}
                  checked={selected?.includes(item.id) ?? false}
                  onChange={() => onToggle?.(item.id)}
                />
              )}
              <Badge tone="warn">{item.signal_type}</Badge>
              <Badge tone="neutral">{item.fraud_family}</Badge>
              <span className="muted">
                {item.detector_id} v{item.detector_version}
              </span>
              <span className="muted">
                log LR {item.log_likelihood_ratio.toFixed(2)}
                {contribution && ` · weighted ${contribution.contributed_log_odds.toFixed(2)}`}
              </span>
              <span style={{ marginLeft: "auto" }}>
                <Timestamp value={item.generated_at} />
              </span>
            </header>

            <div className="evidence__reading">
              <div className="reading reading--incriminating">
                <span className="reading__label">What the detector saw</span>
                <p>{item.explanation}</p>
              </div>
              {contribution && (
                <div className="reading reading--benign">
                  <span className="reading__label">Innocent reading of the same signal</span>
                  <p>{contribution.benign_explanation}</p>
                </div>
              )}
            </div>
          </article>
        );
      })}
    </>
  );
}

export function AssessmentSummary({ assessment }: { assessment: RiskAssessmentView }) {
  return (
    <div className="evidence">
      <header className="evidence__head">
        <Badge>{assessment.confidence}</Badge>
        <span className="muted">ruleset v{assessment.ruleset_version}</span>
        <span className="muted">
          prior {assessment.prior_log_odds.toFixed(2)} → posterior{" "}
          {assessment.posterior_log_odds.toFixed(2)} log-odds
        </span>
        <span style={{ marginLeft: "auto" }}>
          <Timestamp value={assessment.generated_at} />
        </span>
      </header>
      <p className="empty">
        Graded confidence over accumulated evidence, for a human reviewer to weigh. It is not a
        finding, and re-assessing appends a new one rather than rewriting this.
      </p>
    </div>
  );
}
