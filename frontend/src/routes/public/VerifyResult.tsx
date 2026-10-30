import { useState } from "react";
import { Link, Navigate, useLocation } from "react-router-dom";

import { Icon } from "../../components/icons";
import type { IconName } from "../../components/icons";
import { Container, toneFor } from "../../components/ui";
import type { VerificationState, VerifyResponse } from "../../api/types";
import { STATE_PRESENTATION, groupSerial } from "../../lib/verification";

const EXPLANATION: Record<VerificationState, string> = {
  GENUINE:
    "The code verified and nothing has been flagged against it. This is not a guarantee about the contents of the bottle in your hand.",
  CAUTION:
    "The code verified, but something about it warrants a closer look. This is not an accusation — it may simply need manual review.",
  INVALID: "This code did not verify. It may not be a registered Bharosa product, or something about it doesn't match.",
  ALREADY_REPORTED: "A prior report already exists against this identity.",
  UNAVAILABLE: "The verification system could not complete this check. Please try again shortly.",
};

const GLYPH: Record<VerificationState, IconName> = {
  GENUINE: "check",
  CAUTION: "alert",
  INVALID: "cross",
  ALREADY_REPORTED: "info",
  UNAVAILABLE: "more",
};

export function VerifyResult() {
  const location = useLocation();
  const state = location.state as { result?: VerifyResponse; shown?: string } | null;
  const result = state?.result;
  const [expanded, setExpanded] = useState(false);

  if (!result) {
    return <Navigate to="/verify" replace />;
  }

  const presentation = STATE_PRESENTATION[result.state];
  const shown = state?.shown;

  return (
    <Container>
      <div className="verify-result-page">
        <div className={`verdict verdict--${toneFor(result.state)}`}>
          <span className="verdict__ring" aria-hidden="true">
            <Icon name={GLYPH[result.state] ?? "info"} size={44} />
          </span>
          <span className="verdict__eyebrow">This pack</span>
          <h1 className="verdict__state">{presentation?.verdict ?? result.state}</h1>
          <p className="verdict__message">{result.message}</p>

          {shown && (
            <div className="verdict__code">
              <span className="verdict__code-label">Code checked</span>
              <span className="verdict__serial">{groupSerial(shown)}</span>
              <span className="verdict__time">{new Date(result.checked_at).toLocaleString()}</span>
            </div>
          )}
          {!shown && (
            <span className="verdict__time">
              Checked {new Date(result.checked_at).toLocaleString()}
            </span>
          )}
        </div>

        <div className={`verdict-explainer${expanded ? " is-open" : ""}`}>
          <button
            type="button"
            className="verdict-explainer__trigger"
            aria-expanded={expanded}
            onClick={() => setExpanded((open) => !open)}
          >
            {expanded ? "Show less" : "What does this mean?"}
            <span className="disclosure__sign" aria-hidden="true" />
          </button>
          {expanded && (
            <div className="verdict-explainer__body">
              {presentation && <p className="verdict-explainer__action">{presentation.action}</p>}
              <p>{EXPLANATION[result.state] ?? result.message}</p>
              <p className="muted">
                Checking the same pack more than once is normal and counts against nobody.
              </p>
            </div>
          )}
        </div>

        <Link to="/verify" className="button button--secondary button--block button--lg">
          Check another product
        </Link>
      </div>
    </Container>
  );
}
