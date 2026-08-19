import { NavLink, Outlet } from "react-router-dom";

import { system } from "../api/endpoints";
import { useResource } from "../hooks/useResource";
import { useSession } from "../session/SessionContext";
import { Badge, Mono } from "./ui";

const NAV_GROUPS: { label: string; links: { to: string; label: string }[] }[] = [
  {
    label: "Overview",
    links: [
      { to: "/", label: "Dashboard" },
      { to: "/session", label: "Tenant & actor" },
    ],
  },
  {
    label: "Manufacturing",
    links: [
      { to: "/keys", label: "Signing keys" },
      { to: "/catalogue", label: "Products & batches" },
      { to: "/identities", label: "Identities" },
    ],
  },
  {
    label: "Distribution",
    links: [
      { to: "/supply-chain", label: "Supply chain" },
      { to: "/custody-graph", label: "Custody graph" },
    ],
  },
  {
    label: "Integrity",
    links: [
      { to: "/verify", label: "Public verification" },
      { to: "/investigations", label: "Investigations" },
    ],
  },
  {
    label: "Tooling",
    links: [{ to: "/console", label: "API console" }],
  },
];

function HealthIndicator() {
  const ready = useResource(() => system.ready(), []);
  const tone = ready.loading ? "" : ready.error ? "health__dot--bad" : "health__dot--good";
  const label = ready.loading ? "checking" : ready.error ? "unreachable" : "database ready";
  return (
    <span className="health">
      <span className={`health__dot ${tone}`} />
      {label}
    </span>
  );
}

export function Layout() {
  const { session, isConfigured } = useSession();

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand__name">Bharosa</span>
          <span className="brand__tag">console</span>
        </div>

        <nav className="nav">
          {NAV_GROUPS.map((group) => (
            <div key={group.label}>
              <div className="nav__group">{group.label}</div>
              {group.links.map((link) => (
                <NavLink
                  key={link.to}
                  to={link.to}
                  end={link.to === "/"}
                  className={({ isActive }) => `nav__link${isActive ? " is-active" : ""}`}
                >
                  {link.label}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>

        <div className="sidebar__foot">
          <HealthIndicator />
          <span>Development credentials. Not authentication.</span>
        </div>
      </aside>

      <div className="main">
        <header className="topbar">
          <div className="topbar__identity">
            {isConfigured ? (
              <>
                <strong>{session.manufacturerName || "Manufacturer"}</strong>
                <Mono value={session.manufacturerId} short />
                <span>
                  acting as <strong>{session.actorId}</strong>
                </span>
                <Badge tone="info">{session.capabilities.length} capabilities</Badge>
              </>
            ) : (
              <>
                <Badge tone="warn">No tenant selected</Badge>
                <NavLink to="/session">Set one up</NavLink>
              </>
            )}
          </div>
          <NavLink to="/verify" className="nav__link">
            Consumer view
          </NavLink>
        </header>

        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
