import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { Icon } from "../icons";
import { ALL_LINKS } from "./workspaceNav";

// Jump to any workspace page by name. Opens with Ctrl+K / Cmd+K.
export function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [cursor, setCursor] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const matches = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return ALL_LINKS;
    return ALL_LINKS.filter(
      (link) => link.label.toLowerCase().includes(needle) || link.group.toLowerCase().includes(needle),
    );
  }, [query]);

  useEffect(() => {
    if (!open) return;
    setQuery("");
    setCursor(0);
    inputRef.current?.focus();
  }, [open]);

  useEffect(() => {
    setCursor(0);
  }, [query]);

  if (!open) return null;

  const go = (to: string) => {
    onClose();
    navigate(to);
  };

  return (
    <div className="palette" role="dialog" aria-modal="true" aria-label="Go to page" onClick={onClose}>
      <div className="palette__panel" onClick={(event) => event.stopPropagation()}>
        <div className="palette__search">
          <Icon name="search" size={18} />
          <input
            ref={inputRef}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Go to a page…"
            aria-label="Search pages"
            onKeyDown={(event) => {
              if (event.key === "ArrowDown") {
                event.preventDefault();
                setCursor((value) => Math.min(value + 1, matches.length - 1));
              } else if (event.key === "ArrowUp") {
                event.preventDefault();
                setCursor((value) => Math.max(value - 1, 0));
              } else if (event.key === "Enter" && matches[cursor]) {
                event.preventDefault();
                go(matches[cursor].to);
              } else if (event.key === "Escape") {
                onClose();
              }
            }}
          />
          <kbd className="kbd">Esc</kbd>
        </div>
        <ul className="palette__list" role="listbox">
          {matches.length === 0 && <li className="palette__empty">No page matches “{query}”.</li>}
          {matches.map((link, index) => (
            <li key={link.to} role="option" aria-selected={index === cursor}>
              <button
                type="button"
                className={`palette__item${index === cursor ? " is-active" : ""}`}
                onMouseEnter={() => setCursor(index)}
                onClick={() => go(link.to)}
              >
                <Icon name={link.icon} size={18} />
                <span className="palette__label">{link.label}</span>
                <span className="palette__group">{link.group}</span>
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
