import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";

import { BrandMark } from "../ui";

const NAV_LINKS = [
  { to: "/", label: "Home", end: true },
  { to: "/how-it-works", label: "How it works" },
  { to: "/verify", label: "Verify a product" },
  { to: "/about", label: "About" },
  { to: "/contact", label: "Contact" },
];

const FOOTER_PRODUCT_LINKS = [
  { to: "/how-it-works", label: "How it works" },
  { to: "/verify", label: "Verify a product" },
];

const FOOTER_COMPANY_LINKS = [
  { to: "/about", label: "About" },
  { to: "/contact", label: "Contact" },
];

const FOOTER_LEGAL_LINKS = [
  { to: "/legal/privacy", label: "Privacy policy" },
  { to: "/legal/terms", label: "Terms of service" },
];

export function PublicShell() {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div className="pub">
      <header className="pub-header">
        <div className="container pub-header__row">
          <NavLink to="/" className="pub-header__brand brand-lockup" onClick={() => setMenuOpen(false)}>
            <BrandMark />
            <span className="brand-lockup__text">
              <span className="brand-lockup__name">BHAROSA</span>
            </span>
          </NavLink>

          <nav className="pub-header__nav" aria-label="Primary">
            {NAV_LINKS.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                end={link.end}
                className={({ isActive }) => (isActive ? "is-active" : undefined)}
              >
                {link.label}
              </NavLink>
            ))}
          </nav>

          <div className="pub-header__actions">
            <NavLink to="/app/login" className="button button--secondary">
              Sign in
            </NavLink>
            <button
              type="button"
              className="pub-header__toggle"
              aria-expanded={menuOpen}
              aria-label={menuOpen ? "Close menu" : "Open menu"}
              onClick={() => setMenuOpen((value) => !value)}
            >
              {menuOpen ? "\u2715" : "\u2630"}
            </button>
          </div>
        </div>

        {menuOpen && (
          <div className="container">
            <nav className="pub-header__mobile-nav" aria-label="Primary mobile">
              {NAV_LINKS.map((link) => (
                <NavLink key={link.to} to={link.to} end={link.end} onClick={() => setMenuOpen(false)}>
                  {link.label}
                </NavLink>
              ))}
            </nav>
          </div>
        )}
      </header>

      <main>
        <Outlet />
      </main>

      <footer className="pub-footer">
        <div className="container pub-footer__grid">
          <div className="stack pub-footer__brand" style={{ gap: "var(--space-3)" }}>
            <span className="brand-lockup">
              <BrandMark size={22} />
              <span className="brand-lockup__name" style={{ color: "var(--color-ink-text)" }}>
                Bharosa
              </span>
            </span>
            <p className="muted" style={{ fontSize: "0.85rem", maxWidth: "36ch" }}>
              Behavioral integrity for physical goods — proving not just that a code is valid, but
              that the product carrying it behaves like one genuine object.
            </p>
          </div>

          <nav className="pub-footer__col" aria-label="Product">
            <span className="pub-footer__col-title">Product</span>
            {FOOTER_PRODUCT_LINKS.map((link) => (
              <NavLink key={link.to} to={link.to}>
                {link.label}
              </NavLink>
            ))}
          </nav>

          <nav className="pub-footer__col" aria-label="Company">
            <span className="pub-footer__col-title">Company</span>
            {FOOTER_COMPANY_LINKS.map((link) => (
              <NavLink key={link.to} to={link.to}>
                {link.label}
              </NavLink>
            ))}
          </nav>

          <nav className="pub-footer__col" aria-label="Legal">
            <span className="pub-footer__col-title">Legal</span>
            {FOOTER_LEGAL_LINKS.map((link) => (
              <NavLink key={link.to} to={link.to}>
                {link.label}
              </NavLink>
            ))}
          </nav>
        </div>

        <div className="container pub-footer__base">
          <span className="muted" style={{ fontSize: "0.78rem" }}>
            © {new Date().getFullYear()} Bharosa. Behavioral integrity for physical goods.
          </span>
        </div>
      </footer>
    </div>
  );
}
