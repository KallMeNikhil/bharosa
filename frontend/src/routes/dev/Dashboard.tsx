import { Link } from "react-router-dom";

import { identity, intelligence, supplyChain } from "../../api/endpoints";
import { Badge, Card, Empty, ErrorNote, Loading, Mono, Stat, Table, Timestamp } from "../../components/ui";
import { useResource } from "../../hooks/useResource";
import { useSession } from "../../session/SessionContext";
import { NoTenant } from "./NoTenant";

export function Dashboard() {
  const { credential, isConfigured, session } = useSession();

  const products = useResource(() => identity.listProducts(), [credential], {
    enabled: isConfigured,
  });
  const batches = useResource(() => identity.listBatches(), [credential], {
    enabled: isConfigured,
  });
  const identities = useResource(() => identity.listIdentities({ limit: 500 }), [credential], {
    enabled: isConfigured,
  });
  const participants = useResource(() => supplyChain.listParticipants(), [credential], {
    enabled: isConfigured,
  });
  const investigations = useResource(() => intelligence.listInvestigations(), [credential], {
    enabled: isConfigured,
  });

  if (!isConfigured) return <NoTenant />;

  const rows = identities.data ?? [];
  const activated = rows.filter((row) => row.lifecycle_state === "ACTIVATED").length;
  const open = (investigations.data ?? []).filter(
    (incident) => incident.status === "OPEN" || incident.status === "UNDER_REVIEW",
  );

  return (
    <>
      <div className="page-head">
        <div>
          <h1>{session.manufacturerName || "Dashboard"}</h1>
          <p>
            Everything below is scoped to this manufacturer by the database itself, not by the
            queries on this page.
          </p>
        </div>
      </div>

      <div className="grid-3">
        <Stat label="Products" value={products.data?.length ?? "—"} />
        <Stat label="Batches" value={batches.data?.length ?? "—"} />
        <Stat label="Identities" value={rows.length || "—"} />
        <Stat label="Activated" value={activated || "—"} tone={activated ? "good" : undefined} />
        <Stat label="Participants" value={participants.data?.length ?? "—"} />
        <Stat
          label="Live investigations"
          value={open.length || "—"}
          tone={open.length ? "warn" : undefined}
        />
      </div>

      <div className="grid-2">
        <Card
          title="Live investigations"
          subtitle="Graded findings for a human reviewer, never a verdict."
          actions={<Link to="/investigations">All incidents</Link>}
          wide
        >
          <ErrorNote>{investigations.error}</ErrorNote>
          {investigations.loading && <Loading />}
          {!investigations.loading && open.length === 0 && (
            <Empty>Nothing is under investigation.</Empty>
          )}
          {open.length > 0 && (
            <Table
              head={
                <tr>
                  <th>Status</th>
                  <th>Summary</th>
                  <th>Opened</th>
                  <th />
                </tr>
              }
            >
              {open.map((incident) => (
                <tr key={incident.id}>
                  <td>
                    <Badge>{incident.status}</Badge>
                  </td>
                  <td>{incident.summary}</td>
                  <td>
                    <Timestamp value={incident.opened_at} />
                  </td>
                  <td>
                    <Link to={`/investigations/${incident.id}`}>Review</Link>
                  </td>
                </tr>
              ))}
            </Table>
          )}
        </Card>

        <Card
          title="Recent identities"
          actions={<Link to="/identities">All identities</Link>}
          wide
        >
          <ErrorNote>{identities.error}</ErrorNote>
          {identities.loading && <Loading />}
          {!identities.loading && rows.length === 0 && (
            <Empty>
              No identities yet. Reserve some under <Link to="/identities">Identities</Link>, or
              seed a demonstration tenant from <Link to="/session">Tenant and actor</Link>.
            </Empty>
          )}
          {rows.length > 0 && (
            <Table
              head={
                <tr>
                  <th>Serial</th>
                  <th>State</th>
                  <th>Created</th>
                  <th />
                </tr>
              }
            >
              {rows
                .slice()
                .reverse()
                .slice(0, 8)
                .map((row) => (
                  <tr key={row.id}>
                    <td>
                      <Mono value={row.serial} />
                    </td>
                    <td>
                      <Badge>{row.lifecycle_state}</Badge>
                    </td>
                    <td>
                      <Timestamp value={row.created_at} />
                    </td>
                    <td>
                      <Link to={`/identities/${row.id}`}>Open</Link>
                    </td>
                  </tr>
                ))}
            </Table>
          )}
        </Card>
      </div>
    </>
  );
}
