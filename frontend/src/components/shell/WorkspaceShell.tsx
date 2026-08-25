import { useEffect, useState } from "react";
import { NavLink, Outlet } from "react-router-dom";

import { system } from "../../api/endpoints";
import { useResource } from "../../hooks/useResource";
import { useSession } from "../../session/SessionContext";
import { BrandMark, Mono } from "../ui";

interface NavGroup {
  label: string;
  links: { to: string; label: string; end?: boolean }[];
}

const NAV_GROUPS: NavGroup[] = [
  { label: "Overview", links: [{ to: "/app", label: "Overview", end: true }] },
  {
    label: "Products",
    links: [
      { to: "/app/products", label: "Products" },
      { to: "/app/batches", label: "Batches" },
      { to: "/app/identities", label: "Identities" },
    ],
  },
  {
    label: "Supply chain",
    links: [
      { to: "/app/supply-chain", label: "Supply chain" },
      { to: "/app/custody-graph", label: "Custody graph" },
    ],
  },
  {
    label: "Trust & verification",
    links: [{ to: "/app/verification-activity", label: "Verification activity" }],
  },
  {
    label: "Intelligence",
    links: [
      { to: "/app/risk", label: "Risk" },
      { to: "/app/investigations", label: "Investigations" },
    ],
  },
  { label: "Simulation", links: [{ to: "/app/simulation", label: "Simulation" }] },
  {
    label: "Settings",
    links: [
      { to: "/app/settings", label: "Settings" },
      { to: "/app/keys", label: "Signing keys" },
      { to: "/app/help", label: "Help" },
    ],
  },
];

const BOTTOM_LINKS = [
  { to: "/app", label: "Overview", end: true },
  { to: "/app/products", label: "Products" },
  { to: "/app/supply-chain", label: "Supply chain" },
  { to: "/app/risk", label: "Intelligence" },
];

const MORE_LINKS = [
  { to: "/app/verification-activity", label: "Verification activity" },
  { to: "/app/investigations", label: "Investigations" },
  { to: "/app/custody-graph", label: "Custody graph" },
  { to: "/app/simulation", label: "Simulation" },
  { to: "/app/settings", label: "Settings" },
  { to: "/app/keys", label: "Signing keys" },
  { to: "/app/help", label: "Help" },
];

export function WorkspaceShell() {
  const { session, reset } = useSession();
  const [moreOpen, setMoreOpen] = useState(false);
  const health = useResource(() => system.health(), []);

  useEffect(() => {
    if (!moreOpen) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMoreOpen(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [moreOpen]);

  return (
    <div className="ws">
      <aside className="ws-sidebar">
        <div className="ws-sidebar__brand brand-lockup">
          <BrandMark size={24} />
          <span className="brand-lockup__text">
            <span className="brand-lockup__name">Bharosa</span>
            <span className="brand-lockup__tag">Workspace</span>
          </span>
        </div>

        <nav className="stack" style={{ gap: "2px" }} aria-label="Primary">
          {NAV_GROUPS.map((group) => (
            <div key={group.label}>
              <div className="ws-nav__group">{group.label}</div>
              {group.links.map((link) => (
                <NavLink
                  key={link.to}
                  to={link.to}
                  end={link.end}
                  className={({ isActive }) => `ws-nav__link${isActive ? " is-active" : ""}`}
                >
                  {link.label}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>

        <button type="button" className="button button--ghost" onClick={reset} style={{ marginTop: "auto" }}>
          Sign out
        </button>
      </aside>

      <div className="ws-main">
        <header className="ws-topbar">
          <div className="ws-topbar__left">
            <div className="ws-topbar__brand brand-lockup">
              <BrandMark size={22} />
              <span className="brand-lockup__name">Bharosa</span>
            </div>
            <div className="ws-topbar__org">
              <strong>{session.manufacturerName || "Workspace"}</strong>
              <Mono value={session.manufacturerId} short />
            </div>
          </div>
          <div className="cluster">
            <span className="muted" style={{ fontSize: "0.8rem" }}>
              {session.actorId}
            </span>
            <span className="health" title={health.error ? "Service unreachable" : "Service reachable"}>
              <span className={`health__dot ${health.loading ? "" : health.error ? "health__dot--bad" : "health__dot--good"}`} />
            </span>
          </div>
        </header>

        <main className="ws-content">
          <Outlet />
        </main>
      </div>

      <nav className="ws-bottom-nav" aria-label="Primary mobile">
        {BOTTOM_LINKS.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            end={link.end}
            className={({ isActive }) => `ws-bottom-nav__link${isActive ? " is-active" : ""}`}
          >
            {link.label}
          </NavLink>
        ))}
        <button
          type="button"
          className="ws-bottom-nav__link"
          onClick={() => setMoreOpen(true)}
          aria-haspopup="true"
          aria-expanded={moreOpen}
        >
          More
        </button>
      </nav>

      {moreOpen && (
        <div
          className="ws-more-sheet"
          role="dialog"
          aria-modal="true"
          aria-label="More navigation"
          onClick={() => setMoreOpen(false)}
        >
          <div className="ws-more-sheet__panel" onClick={(event) => event.stopPropagation()}>
            {MORE_LINKS.map((link) => (
              <NavLink key={link.to} to={link.to} className="ws-nav__link" onClick={() => setMoreOpen(false)}>
                {link.label}
              </NavLink>
            ))}
            <button type="button" className="button button--ghost" onClick={reset}>
              Sign out
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
