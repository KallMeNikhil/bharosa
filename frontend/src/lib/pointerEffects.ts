// Pointer-driven surface effects, wired once for the whole app.
//
// Surfaces matching GLOW get --mx/--my, the pointer position inside them, which
// the stylesheet turns into a soft light that follows the cursor. Surfaces
// matching TILT also get --rx/--ry for a slight 3D lean. Using one delegated
// listener keeps every page interactive without per-component wiring.

const GLOW = [
  ".card",
  ".stat",
  ".fraud-class-strip__item",
  ".fraud-pattern",
  ".layer-model__panel",
  ".layer-model__item",
  ".verify-form",
  ".verify-steps__step",
  ".not-list li",
  ".evidence",
  ".chain__panel",
  ".honesty",
  ".verdict-explainer",
  ".button--primary",
  ".palette__panel",
].join(",");

const TILT = ".fraud-class-strip__item, .role-card";
const MAX_TILT_DEG = 5;

export function installPointerEffects(): () => void {
  if (typeof window === "undefined" || !window.matchMedia?.("(hover: hover)").matches) {
    return () => undefined;
  }
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  let tilted: HTMLElement | null = null;
  let frame = 0;
  let pending: PointerEvent | null = null;

  const settle = (element: HTMLElement | null) => {
    if (!element) return;
    element.style.setProperty("--rx", "0deg");
    element.style.setProperty("--ry", "0deg");
  };

  const apply = () => {
    frame = 0;
    const event = pending;
    if (!event || !(event.target instanceof Element)) return;

    const glow = event.target.closest<HTMLElement>(GLOW);
    if (glow) {
      const rect = glow.getBoundingClientRect();
      glow.style.setProperty("--mx", `${event.clientX - rect.left}px`);
      glow.style.setProperty("--my", `${event.clientY - rect.top}px`);
    }

    const tilt = reduceMotion ? null : event.target.closest<HTMLElement>(TILT);
    if (tilt !== tilted) {
      settle(tilted);
      tilted = tilt;
    }
    if (tilt) {
      const rect = tilt.getBoundingClientRect();
      const x = (event.clientX - rect.left) / rect.width - 0.5;
      const y = (event.clientY - rect.top) / rect.height - 0.5;
      tilt.style.setProperty("--rx", `${(-y * MAX_TILT_DEG).toFixed(2)}deg`);
      tilt.style.setProperty("--ry", `${(x * MAX_TILT_DEG).toFixed(2)}deg`);
    }
  };

  const onMove = (event: PointerEvent) => {
    pending = event;
    if (!frame) frame = requestAnimationFrame(apply);
  };
  const onLeave = () => {
    settle(tilted);
    tilted = null;
  };

  document.addEventListener("pointermove", onMove, { passive: true });
  document.documentElement.addEventListener("pointerleave", onLeave);
  return () => {
    cancelAnimationFrame(frame);
    document.removeEventListener("pointermove", onMove);
    document.documentElement.removeEventListener("pointerleave", onLeave);
  };
}
