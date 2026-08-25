import { Link } from "react-router-dom";

import { intelligence } from "../../api/endpoints";
import { Badge, Button, Card, Empty, ErrorNote, Loading, Mono, Table, Timestamp } from "../../components/ui";
import { useResource } from "../../hooks/useResource";
import { useSession } from "../../session/SessionContext";
import { NoTenant } from "./NoTenant";

export function Investigations() {
  const { credential, isConfigured } = useSession();
  const incidents = useResource(() => intelligence.listInvestigations(), [credential], {
    enabled: isConfigured,
  });

  if (!isConfigured) return <NoTenant />;

  const rows = incidents.data ?? [];

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Investigations</h1>
          <p>
            Each incident cites the evidence it rests on and can be read on the terms it was
            decided under, because detector output is versioned and never reinterpreted after
            the fact.
          </p>
        </div>
      </div>

      <Card title="All incidents" actions={<Button onClick={incidents.reload}>Refresh</Button>}>
        <ErrorNote>{incidents.error}</ErrorNote>
        {incidents.loading && <Loading />}
        {!incidents.loading && rows.length === 0 && (
          <Empty>
            Nothing has been opened. Incidents start from a risk assessment on an identity.
          </Empty>
        )}
        {rows.length > 0 && (
          <Table
            head={
              <tr>
                <th>Status</th>
                <th>Summary</th>
                <th>Identity</th>
                <th>Opened by</th>
                <th>Opened</th>
                <th>Resolved</th>
                <th />
              </tr>
            }
          >
            {rows.map((incident) => (
              <tr key={incident.id}>
                <td>
                  <Badge>{incident.status}</Badge>
                </td>
                <td>{incident.summary}</td>
                <td>
                  <Link to={`/identities/${incident.identity_id}`}>
                    <Mono value={incident.identity_id} short />
                  </Link>
                </td>
                <td>{incident.opened_by}</td>
                <td>
                  <Timestamp value={incident.opened_at} />
                </td>
                <td>
                  <Timestamp value={incident.resolved_at} />
                </td>
                <td>
                  <Link to={`/investigations/${incident.id}`}>Review</Link>
                </td>
              </tr>
            ))}
          </Table>
        )}
      </Card>
    </>
  );
}
