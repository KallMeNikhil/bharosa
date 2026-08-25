import { useState } from "react";

import { LAYERS } from "./layerData";

export function LayerModel({ compact = false }: { compact?: boolean }) {
  const [activeIndex, setActiveIndex] = useState(0);
  const active = LAYERS[activeIndex];

  return (
    <div className="layer-model">
      <div className="layer-model__list" role="tablist" aria-label="Verification layers">
        {LAYERS.map((layer, index) => (
          <button
            key={layer.name}
            type="button"
            role="tab"
            aria-selected={index === activeIndex}
            className={`layer-model__item${index === activeIndex ? " is-active" : ""}`}
            onClick={() => setActiveIndex(index)}
          >
            <span className="layer-model__badge">{layer.index}</span>
            <span className="layer-model__name">{layer.name}</span>
          </button>
        ))}
      </div>

      <div className="layer-model__panel" role="tabpanel">
        <div>
          <span className="eyebrow">{active.name}</span>
          <p className="layer-model__question">{active.question}</p>
        </div>
        <div className="layer-model__row">
          <div className="layer-model__col layer-model__col--proves">
            <span className="layer-model__col-label">Proves</span>
            <p className="muted">{active.proves}</p>
          </div>
          <div className="layer-model__col layer-model__col--not">
            <span className="layer-model__col-label">Does not prove</span>
            <p className="muted">{active.notProves}</p>
          </div>
        </div>
        {!compact && (
          <p className="muted" style={{ fontSize: "0.85rem" }}>
            Each layer can independently pass or fail. A conclusion that something is fraudulent
            is only ever drawn across layers, with the specific evidence that supports it.
          </p>
        )}
      </div>
    </div>
  );
}
