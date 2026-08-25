import { Link } from "react-router-dom";

import { identity, intelligence, supplyChain } from "../../api/endpoints";
import { LifecycleTrack } from "../../components/LifecycleTrack";
import {
  Badge,
  Card,
  Empty,
  ErrorNote,
  Loading,
  Mono,
  PageHeader,
  Stat,
  Table,
  Timestamp,
} from "../../components/ui";
import { useResource } from "../../hooks/useResource";
import { useSession } from "../../session/SessionContext";

export function Overview() {
  const { credential, session } = useSession();

  const products = useResource(() => identity.listProducts(), [credential]);
  const batches = useResource(() => identity.listBatches(), [credential]);
  const identities = useResource(() => identity.listIdentities({ limit: 500 }), [credential]);
  const participants = useResource(() => supplyChain.listParticipants(), [credential]);
  const investigations = useResource(() => intelligence.listInvestigations(), [credential]);

  const rows = identities.data ?? [];
  const activated = rows.filter((row) => row.lifecycle_state === "ACTIVATED").length;
  const open = (investigations.data ?? []).filter(
    (incident) => incident.status === "OPEN" || incident.status === "UNDER_REVIEW",
  );
  const activationRate = rows.length ? Math.round((activated / rows.length) * 100) : null;
  const trustClear = open.length === 0;

  return (
    <>
      <PageHeader
        eyebrow="Overview"
        title={session.manufacturerName || "Overview"}
        description="Everything below is scoped to this manufacturer by the database itself, not by the queries on this page."
      />

      <div
        className="ink-surface card--wide"
        style={{
          borderRadius: "var(--radius)",
          padding: "var(--space-5)",
          display: "flex",
          flexWrap: "wrap",
          gap: "var(--space-6)",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <div>
          <span className="eyebrow" style={{ color: "var(--color-ink-accent)" }}>
            Identity activation
          </span>
          <div style={{ display: "flex", alignItems: "baseline", gap: "var(--space-2)", marginTop: "4px" }}>
            <span style={{ fontSize: "2.2rem", fontWeight: 700 }}>
              {activationRate === null ? "—" : `${activationRate}%`}
            </span>
            <span className="muted">
              {activated} of {rows.length || 0} identities activated
            </span>
          </div>
        </div>

        <div style={{ textAlign: "right" }}>
          <span className="eyebrow" style={{ color: "var(--color-ink-accent)" }}>
            Trust status
          </span>
          <div style={{ marginTop: "4px" }}>
            <Badge tone={trustClear ? "good" : "warn"}>
              {trustClear ? "Clear — nothing under investigation" : `${open.length} live investigation${open.length === 1 ? "" : "s"}`}
            </Badge>
          </div>
        </div>
      </div>

      <div className="grid-3">
        <Stat label="Products" value={products.data?.length ?? "—"} />
        <Stat label="Batches" value={batches.data?.length ?? "—"} />
        <Stat label="Participants" value={participants.data?.length ?? "—"} />
      </div>

      <div className="grid-2">
        <Card
          title="Live investigations"
          subtitle="Graded findings for a human reviewer, never a verdict."
          actions={<Link to="/app/investigations">All incidents</Link>}
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
                    <Link to={`/app/investigations/${incident.id}`}>Review</Link>
                  </td>
                </tr>
              ))}
            </Table>
          )}
        </Card>

        <Card title="Recent identities" actions={<Link to="/app/identities">All identities</Link>} wide>
          <ErrorNote>{identities.error}</ErrorNote>
          {identities.loading && <Loading />}
          {!identities.loading && rows.length === 0 && (
            <Empty>
              No identities yet. Reserve some under <Link to="/app/identities">Identities</Link>.
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
                      <LifecycleTrack state={row.lifecycle_state} />
                    </td>
                    <td>
                      <Timestamp value={row.created_at} />
                    </td>
                    <td>
                      <Link to={`/app/identities/${row.id}`}>Open</Link>
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
