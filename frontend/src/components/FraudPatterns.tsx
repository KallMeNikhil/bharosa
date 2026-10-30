import type { CSSProperties } from "react";

import { Reveal } from "./ui";

interface FraudPattern {
  name: string;
  body: string;
  sequence: ("ok" | "break" | "flag")[];
  caption: string;
}

const PATTERNS: FraudPattern[] = [
  {
    name: "Full counterfeit",
    body: "An identity that was never legitimately issued by a manufacturer at all.",
    sequence: ["flag", "break", "break"],
    caption: "No legitimate issuance ever exists behind it.",
  },
  {
    name: "Code cloning",
    body: "A legitimately issued identity reproduced onto multiple physical objects.",
    sequence: ["ok", "ok", "break", "flag"],
    caption: "The same identity, scanned somewhere it couldn't physically have traveled.",
  },
  {
    name: "Refilling",
    body: "A genuine container reused with unauthorized contents after its legitimate lifecycle should have ended.",
    sequence: ["ok", "ok", "ok", "break", "flag"],
    caption: "A fresh-looking event where the object's life should already be over.",
  },
  {
    name: "Diversion / grey-market",
    body: "A genuine product moved outside its authorized territory or distribution channel.",
    sequence: ["ok", "ok", "break", "flag"],
    caption: "A custody path that departs from the declared distribution channel.",
  },
];

const STEP_WORDS: Record<FraudPattern["sequence"][number], string> = {
  ok: "expected step",
  break: "anomalous transition",
  flag: "detection point",
};

function describeSequence(pattern: FraudPattern) {
  return `Event sequence: ${pattern.sequence.map((step) => STEP_WORDS[step]).join(", then ")}.`;
}

export function FraudPatterns() {
  return (
    <div className="fraud-patterns">
      <div className="fraud-pattern__legend" aria-hidden="true">
        <span className="fraud-pattern__legend-item">
          <span className="fraud-pattern__legend-swatch fraud-pattern__legend-swatch--ok" />
          Expected step
        </span>
        <span className="fraud-pattern__legend-item">
          <span className="fraud-pattern__legend-swatch fraud-pattern__legend-swatch--break" />
          Anomalous transition
        </span>
        <span className="fraud-pattern__legend-item">
          <span className="fraud-pattern__legend-swatch fraud-pattern__legend-swatch--flag" />
          Detection point
        </span>
      </div>
      <div className="grid-2 grid-2--stretch">
        {PATTERNS.map((pattern, patternIndex) => (
          <Reveal className="fraud-pattern" key={pattern.name} delay={patternIndex % 2 === 0 ? 0 : 1}>
            <div className="fraud-pattern__head">
              <span className="fraud-pattern__index">{String(patternIndex + 1).padStart(2, "0")}</span>
              <h3>{pattern.name}</h3>
              <p className="muted">{pattern.body}</p>
            </div>
            <div
              className="fraud-pattern__diagram"
              role="img"
              aria-label={describeSequence(pattern)}
            >
              {pattern.sequence.map((step, index) => (
                <span
                  key={index}
                  aria-hidden="true"
                  className="fraud-pattern__step"
                  style={{ "--i": index } as CSSProperties}
                >
                  <span
                    className={`fraud-pattern__dot${step === "flag" ? " fraud-pattern__dot--flag" : ""}`}
                  />
                  {index < pattern.sequence.length - 1 && (
                    <span
                      className={`fraud-pattern__link${
                        pattern.sequence[index + 1] === "flag" || step === "break" ? " fraud-pattern__link--break" : ""
                      }`}
                    />
                  )}
                </span>
              ))}
            </div>
            <p className="fraud-pattern__caption">{pattern.caption}</p>
          </Reveal>
        ))}
      </div>
    </div>
  );
}
