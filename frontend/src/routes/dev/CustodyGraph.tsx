import { useState } from "react";

import { identity, intelligence, supplyChain } from "../../api/endpoints";
import { Badge, Button, Card, Empty, ErrorNote, InfoNote, Loading, Mono, Table } from "../../components/ui";
import { useAction, useResource } from "../../hooks/useResource";
import { useSession } from "../../session/SessionContext";
import { NoTenant } from "./NoTenant";
import type { CustodyGraphView } from "../../api/types";

export function CustodyGraph() {
  const { credential, isConfigured } = useSession();

  const identities = useResource(() => identity.listIdentities({ limit: 200 }), [credential], {
    enabled: isConfigured,
  });
  const participants = useResource(() => supplyChain.listParticipants(), [credential], {
    enabled: isConfigured,
  });

  const [selected, setSelected] = useState<string[]>([]);
  const [graph, setGraph] = useState<CustodyGraphView | null>(null);

  const build = useAction(async () => {
    setGraph(await intelligence.custodyGraph(selected));
  });

  if (!isConfigured) return <NoTenant />;

  const rows = identities.data ?? [];
  const label = (participantId: string) => {
    const match = (participants.data ?? []).find((item) => item.id === participantId);
    return match ? `${match.participant_ref} · ${match.name}` : participantId;
  };

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Custody graph</h1>
          <p>
            Derived from the event log at request time and never cached. Where several packs
            share a route and then part company, the deepest node they still shared is where an
            investigator should look first.
          </p>
        </div>
      </div>

      <Card
        title="Choose identities"
        subtitle="A graph over one pack tells you little. Two or more that were supposed to travel together tell you a great deal."
        actions={
          <Button
            variant="primary"
            disabled={selected.length === 0}
            pending={build.pending}
            onClick={() => void build.run()}
          >
            Build graph
          </Button>
        }
      >
        <ErrorNote>{build.error ?? identities.error}</ErrorNote>
        {identities.loading && <Loading />}
        {!identities.loading && rows.length === 0 && <Empty>No identities.</Empty>}
        {rows.length > 0 && (
          <Table
            head={
              <tr>
                <th />
                <th>Serial</th>
                <th>State</th>
              </tr>
            }
          >
            {rows.map((row) => (
              <tr key={row.id} className={selected.includes(row.id) ? "is-selected" : undefined}>
                <td>
                  <input
                    type="checkbox"
                    style={{ width: "auto" }}
                    checked={selected.includes(row.id)}
                    onChange={() =>
                      setSelected((current) =>
                        current.includes(row.id)
                          ? current.filter((value) => value !== row.id)
                          : [...current, row.id],
                      )
                    }
                  />
                </td>
                <td>
                  <Mono value={row.serial} />
                </td>
                <td>
                  <Badge>{row.lifecycle_state}</Badge>
                </td>
              </tr>
            ))}
          </Table>
        )}
      </Card>

      {graph && (
        <Card title="Result">
          {graph.common_divergence_point ? (
            <InfoNote>
              These packs last shared custody at{" "}
              <strong>{label(graph.common_divergence_point)}</strong>. That is a place to look,
              not a finding about anyone there.
            </InfoNote>
          ) : (
            <InfoNote>No shared divergence point across the selected identities.</InfoNote>
          )}

          {graph.edges.length === 0 ? (
            <Empty>No custody movement recorded for these identities.</Empty>
          ) : (
            <Table
              head={
                <tr>
                  <th>From</th>
                  <th>To</th>
                  <th>Identities on this edge</th>
                </tr>
              }
            >
              {graph.edges.map((edge) => (
                <tr key={`${edge.source}-${edge.destination}`}>
                  <td>{label(edge.source)}</td>
                  <td>{label(edge.destination)}</td>
                  <td>
                    <Badge tone={edge.identity_count > 1 ? "info" : "neutral"}>
                      {edge.identity_count}
                    </Badge>
                  </td>
                </tr>
              ))}
            </Table>
          )}
        </Card>
      )}
    </>
  );
}
