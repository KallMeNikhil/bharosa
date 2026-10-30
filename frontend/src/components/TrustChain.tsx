import { Fragment } from "react";

import { useTabs } from "../hooks/useTabs";

const NODES = [
  { label: "Product", detail: "A physical pack, made real to Bharosa the moment it's reserved." },
  { label: "Identity", detail: "A signed, versioned payload — the entry point, never the whole proof." },
  { label: "Verification", detail: "Signature and physical checks, run at the moment someone scans." },
  { label: "Supply chain", detail: "Custody events from manufacturer to retailer, checked against what's declared." },
  { label: "Evidence", detail: "Cited, versioned signals — never a raw score, never a verdict on their own." },
  { label: "Risk / trust", detail: "A graded confidence across every layer, correlated — not a single weak signal." },
];

export function TrustChain() {
  const { active, onKeyDown, tabProps } = useTabs(NODES.length);
  const current = NODES[active];

  return (
    <div className="chain">
      <div
        className="chain__rail"
        role="tablist"
        aria-label="How a product becomes a trust result"
        onKeyDown={onKeyDown}
      >
        {NODES.map((node, index) => (
          <Fragment key={node.label}>
            <button
              {...tabProps(index)}
              className={`chain__node${active === index ? " is-active" : ""}${index < active ? " is-passed" : ""}`}
            >
              <span className="chain__index">{String(index + 1).padStart(2, "0")}</span>
              <span className="chain__label">{node.label}</span>
            </button>
            {index < NODES.length - 1 && (
              <span className={`chain__connector${index < active ? " is-passed" : ""}`} aria-hidden="true" />
            )}
          </Fragment>
        ))}
      </div>

      <div className="chain__panel" role="tabpanel">
        <span className="chain__panel-index">
          {String(active + 1).padStart(2, "0")}/{NODES.length}
        </span>
        <p key={active} className="chain__panel-detail">
          {current.detail}
        </p>
      </div>
    </div>
  );
}
