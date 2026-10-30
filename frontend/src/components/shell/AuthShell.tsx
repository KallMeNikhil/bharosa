import { Link, Outlet } from "react-router-dom";

import { BrandMark } from "../ui";

export function AuthShell() {
  return (
    <div className="auth-shell">
      <aside className="auth-shell__aside ink-band" aria-hidden="true">
        <div className="auth-shell__aside-inner">
          <BrandMark size={72} />
          <p className="auth-shell__tagline">Behavioral integrity for physical goods.</p>
        </div>
      </aside>
      <div className="auth-shell__column">
        <header className="auth-shell__header">
          <Link to="/" className="brand-lockup auth-shell__brand">
            <BrandMark size={30} />
            <span className="brand-lockup__text">
              <span className="brand-lockup__name">BHAROSA</span>
            </span>
          </Link>
        </header>
        <main className="auth-shell__main page-enter">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
