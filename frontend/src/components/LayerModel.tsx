import { useTabs } from "../hooks/useTabs";
import { Icon } from "./icons";
import { LAYERS } from "./layerData";

export function LayerModel({ compact = false }: { compact?: boolean }) {
  const { active: activeIndex, onKeyDown, tabProps } = useTabs(LAYERS.length);
  const active = LAYERS[activeIndex];

  return (
    <div className="layer-model">
      <div className="layer-model__list" role="tablist" aria-label="Verification layers" onKeyDown={onKeyDown}>
        {LAYERS.map((layer, index) => (
          <button
            key={layer.name}
            {...tabProps(index)}
            className={`layer-model__item${index === activeIndex ? " is-active" : ""}`}
          >
            <span className="layer-model__badge">{layer.index}</span>
            <span className="layer-model__name">{layer.name}</span>
          </button>
        ))}
      </div>

      <div className="layer-model__panel" role="tabpanel">
        <div key={activeIndex} className="layer-model__content">
          <div className="layer-model__lead">
            <span className="eyebrow">{active.name}</span>
            <p className="layer-model__question">{active.question}</p>
          </div>
          <div className="layer-model__row">
            <div className="layer-model__col layer-model__col--proves">
              <span className="layer-model__col-label">
                <Icon name="check" size={15} />
                Proves
              </span>
              <p>{active.proves}</p>
            </div>
            <div className="layer-model__col layer-model__col--not">
              <span className="layer-model__col-label">
                <Icon name="cross" size={15} />
                Does not prove
              </span>
              <p>{active.notProves}</p>
            </div>
          </div>
          {!compact && (
            <p className="layer-model__footnote">
              Each layer can independently pass or fail. A conclusion that something is fraudulent
              is only ever drawn across layers, with the specific evidence that supports it.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
