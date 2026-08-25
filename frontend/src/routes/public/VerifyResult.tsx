import { Link, Navigate, useLocation } from "react-router-dom";

import { Container, toneFor } from "../../components/ui";
import type { VerifyResponse } from "../../api/types";

const HEADLINE: Record<string, string> = {
  GENUINE: "Registered",
  CAUTION: "Check before you use this",
  INVALID: "Could not be confirmed",
  ALREADY_REPORTED: "Already reported",
  UNAVAILABLE: "Cannot check right now",
};

const EXPLANATION: Record<string, string> = {
  GENUINE:
    "The code verified and nothing has been flagged against it. This is not a guarantee about the contents of the bottle in your hand.",
  CAUTION:
    "The code verified, but something about it warrants a closer look. This is not an accusation — it may simply need manual review.",
  INVALID: "This code did not verify. It may not be a registered Bharosa product, or something about it doesn't match.",
  ALREADY_REPORTED: "A prior report already exists against this identity.",
  UNAVAILABLE: "The verification system could not complete this check. Please try again shortly.",
};

const GLYPH: Record<string, string> = {
  GENUINE: "\u2713",
  CAUTION: "!",
  INVALID: "\u2715",
  ALREADY_REPORTED: "i",
  UNAVAILABLE: "\u2026",
};

export function VerifyResult() {
  const location = useLocation();
  const state = location.state as { result?: VerifyResponse } | null;
  const result = state?.result;

  if (!result) {
    return <Navigate to="/verify" replace />;
  }

  return (
    <Container>
      <div className="verify-page">
        <div className={`verify-result verify-result--${toneFor(result.state)}`}>
          <div className="verify-result__top">
            <span className="verify-result__ring" aria-hidden="true">
              {GLYPH[result.state] ?? "?"}
            </span>
            <h1 className="verify-result__state">{HEADLINE[result.state] ?? result.state}</h1>
          </div>
          <p className="verify-result__message">{EXPLANATION[result.state] ?? result.message}</p>
          <span className="verify-result__meta">
            Checked {new Date(result.checked_at).toLocaleString()}
          </span>
        </div>

        <Link to="/verify" className="button button--secondary button--block">
          Check another product
        </Link>
      </div>
    </Container>
  );
}
