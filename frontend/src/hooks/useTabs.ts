import { useRef, useState } from "react";
import type { KeyboardEvent } from "react";

// Roving selection for a row of tabs: arrow keys, Home and End move between them.
export function useTabs(count: number) {
  const [active, setActive] = useState(0);
  const refs = useRef<(HTMLButtonElement | null)[]>([]);

  const select = (index: number) => {
    const next = (index + count) % count;
    setActive(next);
    refs.current[next]?.focus();
  };

  const onKeyDown = (event: KeyboardEvent<HTMLElement>) => {
    const moves: Record<string, number> = {
      ArrowRight: active + 1,
      ArrowDown: active + 1,
      ArrowLeft: active - 1,
      ArrowUp: active - 1,
      Home: 0,
      End: count - 1,
    };
    if (!(event.key in moves)) return;
    event.preventDefault();
    select(moves[event.key]);
  };

  const tabProps = (index: number) => ({
    ref: (node: HTMLButtonElement | null) => {
      refs.current[index] = node;
    },
    role: "tab" as const,
    type: "button" as const,
    "aria-selected": active === index,
    tabIndex: active === index ? 0 : -1,
    onClick: () => setActive(index),
  });

  return { active, onKeyDown, tabProps };
}
