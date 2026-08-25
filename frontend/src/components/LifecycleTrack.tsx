import { LIFECYCLE_PATH } from "../api/types";
import type { LifecycleState } from "../api/types";

export function LifecycleTrack({ state }: { state: LifecycleState }) {
  const index = LIFECYCLE_PATH.indexOf(state);

  if (index === -1) {
    return <span className="badge badge--neutral">{state}</span>;
  }

  return (
    <span className="lifecycle-track" title={state}>
      {LIFECYCLE_PATH.map((step, stepIndex) => (
        <span
          key={step}
          className={`lifecycle-track__dot${stepIndex <= index ? " is-reached" : ""}${
            stepIndex === index ? " is-current" : ""
          }`}
        />
      ))}
      <span className="lifecycle-track__label">{state}</span>
    </span>
  );
}
