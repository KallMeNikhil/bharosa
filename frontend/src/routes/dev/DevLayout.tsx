import { NavLink, Outlet } from "react-router-dom";

import { system } from "../../api/endpoints";
import { useResource } from "../../hooks/useResource";
import { useSession } from "../../session/SessionContext";
import { Badge, Mono } from "../../components/ui";

const NAV_GROUPS: { label: string; links: { to: string; label: string }[] }[] = [
  {
    label: "Overview",
    links: [
      { to: "/dev", label: "Dashboard" },
      { to: "/dev/session", label: "Tenant & actor" },
    ],
  },
  {
    label: "Manufacturing",
    links: [
      { to: "/dev/keys", label: "Signing keys" },
      { to: "/dev/catalogue", label: "Products & batches" },
      { to: "/dev/identities", label: "Identities" },
    ],
  },
  {
    label: "Distribution",
    links: [
      { to: "/dev/supply-chain", label: "Supply chain" },
      { to: "/dev/custody-graph", label: "Custody graph" },
    ],
  },
  {
    label: "Integrity",
    links: [
      { to: "/verify", label: "Public verification" },
      { to: "/dev/investigations", label: "Investigations" },
      { to: "/dev/simulation", label: "Simulation" },
    ],
  },
  {
    label: "Tooling",
    links: [{ to: "/dev/console", label: "API console" }],
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

export function DevLayout() {
  const { session, isConfigured } = useSession();

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand__name">Bharosa</span>
          <span className="brand__tag">internal test console</span>
        </div>

        <nav className="nav">
          {NAV_GROUPS.map((group) => (
            <div key={group.label}>
              <div className="nav__group">{group.label}</div>
              {group.links.map((link) => (
                <NavLink
                  key={link.to}
                  to={link.to}
                  end={link.to === "/dev"}
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
          <span>Development credentials. Not authentication. Not the product UI.</span>
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
