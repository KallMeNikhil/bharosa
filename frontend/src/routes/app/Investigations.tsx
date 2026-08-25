import { Link } from "react-router-dom";

import { intelligence } from "../../api/endpoints";
import { Badge, Button, Card, Empty, ErrorNote, Loading, Mono, PageHeader, Table, Timestamp } from "../../components/ui";
import { useResource } from "../../hooks/useResource";
import { useSession } from "../../session/SessionContext";

export function Investigations() {
  const { credential } = useSession();
  const incidents = useResource(() => intelligence.listInvestigations(), [credential]);

  const rows = incidents.data ?? [];

  return (
    <>
      <PageHeader
        eyebrow="Intelligence"
        title="Investigations"
        description="Each incident cites the evidence it rests on and can be read on the terms it was decided under, because detector output is versioned and never reinterpreted after the fact."
      />

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
                  <Link to={`/app/identities/${incident.identity_id}`}>
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
                  <Link to={`/app/investigations/${incident.id}`}>Review</Link>
                </td>
              </tr>
            ))}
          </Table>
        )}
      </Card>
    </>
  );
}
