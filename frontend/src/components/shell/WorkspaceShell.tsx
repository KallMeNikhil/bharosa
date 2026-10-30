import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";

import { auth, identity, system } from "../../api/endpoints";
import { useResource } from "../../hooks/useResource";
import { useSession } from "../../session/SessionContext";
import { Icon } from "../icons";
import { BrandMark, Mono } from "../ui";
import { CommandPalette } from "./CommandPalette";
import { BOTTOM_LINKS, MORE_LINKS, NAV_GROUPS } from "./workspaceNav";

export function WorkspaceShell() {
  const { session, reset, credential } = useSession();
  const [moreOpen, setMoreOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const health = useResource(() => system.health(), []);
  // Ends the session on the server too, so the token cannot be reused.
  const signOut = () => {
    if (session.token) void auth.signOut().catch(() => undefined);
    reset();
  };
  const tenant = useResource(() => identity.ownManufacturer(), [credential]);
  const tenantMissing = Boolean(tenant.error?.startsWith("404"));
  const { pathname } = useLocation();
  const navRef = useRef<HTMLElement>(null);

  // Slides the single active marker to whichever link the route lit up.
  useLayoutEffect(() => {
    const nav = navRef.current;
    const active = nav?.querySelector<HTMLElement>(".ws-nav__link.is-active");
    if (!nav) return;
    nav.style.setProperty("--ind-o", active ? "1" : "0");
    if (!active) return;
    nav.style.setProperty("--ind-y", `${active.offsetTop + 8}px`);
    nav.style.setProperty("--ind-h", `${active.offsetHeight - 16}px`);
  }, [pathname]);

  useEffect(() => {
    setMoreOpen(false);
    window.scrollTo?.({ top: 0 });
  }, [pathname]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setMoreOpen(false);
        setPaletteOpen(false);
      }
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setPaletteOpen((value) => !value);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  const healthLabel = health.loading
    ? "Checking service"
    : health.error
      ? "Service unreachable"
      : "Service reachable";

  return (
    <div className="ws">
      <a className="skip-link" href="#workspace-main">
        Skip to content
      </a>
      <aside className="ws-sidebar">
        <div className="ws-sidebar__brand brand-lockup">
          <BrandMark size={30} />
          <span className="brand-lockup__text">
            <span className="brand-lockup__name">Bharosa</span>
            <span className="brand-lockup__tag">Workspace</span>
          </span>
        </div>

        <button type="button" className="ws-search" onClick={() => setPaletteOpen(true)}>
          <Icon name="search" size={16} />
          <span>Go to…</span>
          <kbd className="kbd">Ctrl K</kbd>
        </button>

        <nav ref={navRef} className="ws-nav" aria-label="Primary">
          <span className="ws-nav__indicator" aria-hidden="true" />
          {NAV_GROUPS.map((group) => (
            <div key={group.label} className="ws-nav__section">
              <div className="ws-nav__group">{group.label}</div>
              {group.links.map((link) => (
                <NavLink
                  key={link.to}
                  to={link.to}
                  end={link.end}
                  className={({ isActive }) => `ws-nav__link${isActive ? " is-active" : ""}`}
                >
                  <Icon name={link.icon} size={18} />
                  {link.label}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>

        <div className="ws-sidebar__foot">
          <div className="ws-sidebar__actor">
            <span className="ws-avatar" aria-hidden="true">
              {(session.actorId || "?").slice(0, 1).toUpperCase()}
            </span>
            <span className="ws-sidebar__actor-text">
              <span className="ws-sidebar__actor-name">{session.actorId}</span>
              <span className="ws-sidebar__actor-org">{session.manufacturerName || "Workspace"}</span>
            </span>
          </div>
          <button type="button" className="button button--ghost ws-signout" onClick={signOut}>
            <Icon name="signout" size={18} />
            Sign out
          </button>
        </div>
      </aside>

      <div className="ws-main">
        <header className="ws-topbar">
          <div className="ws-topbar__left">
            <div className="ws-topbar__brand brand-lockup">
              <BrandMark size={24} />
              <span className="brand-lockup__name">Bharosa</span>
            </div>
            <div className="ws-topbar__org">
              <strong>{session.manufacturerName || "Workspace"}</strong>
              <Mono value={session.manufacturerId} short />
            </div>
          </div>
          <div className="ws-topbar__right">
            <button
              type="button"
              className="ws-topbar__icon-button"
              aria-label="Go to a page"
              onClick={() => setPaletteOpen(true)}
            >
              <Icon name="search" size={18} />
            </button>
            <span className="ws-topbar__actor">{session.actorId}</span>
            <span className="health" title={healthLabel}>
              <span
                className={`health__dot ${health.loading ? "" : health.error ? "health__dot--bad" : "health__dot--good"}`}
              />
              <span className="health__label">{healthLabel}</span>
            </span>
          </div>
        </header>

        <main id="workspace-main" className="ws-content">
          {tenantMissing && (
            <div className="ws-alert" role="alert">
              <span>
                This workspace points at a manufacturer that does not exist, so nothing can be
                saved. The database may have been reset.
              </span>
              <button type="button" className="button button--secondary" onClick={signOut}>
                Sign in again
              </button>
            </div>
          )}
          <div key={pathname} className="ws-page page-enter">
            <Outlet />
          </div>
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
            <Icon name={link.icon} size={20} />
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
          <Icon name="more" size={20} />
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
            <span className="ws-more-sheet__handle" aria-hidden="true" />
            {MORE_LINKS.map((link) => (
              <NavLink key={link.to} to={link.to} className="ws-nav__link" onClick={() => setMoreOpen(false)}>
                <Icon name={link.icon} size={18} />
                {link.label}
              </NavLink>
            ))}
            <button type="button" className="button button--ghost ws-signout" onClick={signOut}>
              <Icon name="signout" size={18} />
              Sign out
            </button>
          </div>
        </div>
      )}

      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
    </div>
  );
}
