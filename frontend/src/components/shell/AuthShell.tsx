import { Link, Outlet } from "react-router-dom";

import { BrandMark } from "../ui";

export function AuthShell() {
  return (
    <div className="auth-shell">
      <header className="auth-shell__header">
        <Link to="/" className="brand-lockup auth-shell__brand">
          <BrandMark />
          <span className="brand-lockup__text">
            <span className="brand-lockup__name">BHAROSA</span>
          </span>
        </Link>
      </header>
      <main className="auth-shell__main">
        <Outlet />
      </main>
    </div>
  );
}
