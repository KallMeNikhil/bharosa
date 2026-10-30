import { useEffect, useRef, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";

import { Icon } from "../icons";
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
  const [scrolled, setScrolled] = useState(false);
  const [tucked, setTucked] = useState(false);
  const headerRef = useRef<HTMLElement>(null);
  const { pathname } = useLocation();
  const isHome = pathname === "/";

  useEffect(() => {
    setMenuOpen(false);
    window.scrollTo?.({ top: 0 });
  }, [pathname]);

  // The header steps aside while reading down the page and returns on the
  // first scroll up. Its bottom edge doubles as a reading-progress line.
  useEffect(() => {
    let lastY = window.scrollY;
    let frame = 0;
    const update = () => {
      frame = 0;
      const y = window.scrollY;
      const room = document.documentElement.scrollHeight - window.innerHeight;
      setScrolled(y > 8);
      setTucked(y > 320 && y > lastY + 2 ? true : y < lastY - 2 ? false : (value) => value);
      headerRef.current?.style.setProperty("--progress", room > 0 ? String(Math.min(y / room, 1)) : "0");
      lastY = y;
    };
    const onScroll = () => {
      if (!frame) frame = requestAnimationFrame(update);
    };
    update();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("scroll", onScroll);
    };
  }, []);

  useEffect(() => {
    if (!menuOpen) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMenuOpen(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [menuOpen]);

  return (
    <div className={`pub${isHome ? " pub--home" : ""}`}>
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <header
        ref={headerRef}
        className={`pub-header${scrolled ? " is-scrolled" : ""}${menuOpen ? " is-menu-open" : ""}${
          tucked && !menuOpen ? " is-tucked" : ""
        }`}
      >
        <div className="container pub-header__row">
          <NavLink to="/" className="pub-header__brand brand-lockup">
            <BrandMark size={30} />
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
              <Icon name={menuOpen ? "close" : "menu"} size={22} />
            </button>
          </div>
        </div>

        {menuOpen && (
          <div className="container">
            <nav className="pub-header__mobile-nav" aria-label="Primary mobile">
              {NAV_LINKS.map((link) => (
                <NavLink
                  key={link.to}
                  to={link.to}
                  end={link.end}
                  className={({ isActive }) => (isActive ? "is-active" : undefined)}
                  onClick={() => setMenuOpen(false)}
                >
                  {link.label}
                  <Icon name="arrow" size={18} />
                </NavLink>
              ))}
            </nav>
          </div>
        )}
      </header>

      <main id="main" className="pub-main">
        <div key={pathname} className="page-enter">
          <Outlet />
        </div>
      </main>

      <footer className="pub-footer">
        <div className="container pub-footer__grid">
          <div className="pub-footer__brand">
            <span className="brand-lockup">
              <BrandMark size={28} />
              <span className="brand-lockup__name">Bharosa</span>
            </span>
            <p className="pub-footer__blurb">
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
          <span>© {new Date().getFullYear()} Bharosa. Behavioral integrity for physical goods.</span>
        </div>
      </footer>
    </div>
  );
}
