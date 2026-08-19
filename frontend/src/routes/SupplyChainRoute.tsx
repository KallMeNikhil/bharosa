import { useState } from "react";

import { supplyChain } from "../api/endpoints";
import { PARTICIPANT_ROLES } from "../api/types";
import type { ParticipantRole } from "../api/types";
import { Badge, Button, Card, Empty, ErrorNote, Field, InfoNote, Loading, Mono, Row, Table, Timestamp } from "../components/ui";
import { useAction, useResource } from "../hooks/useResource";
import { useSession } from "../session/SessionContext";
import { NoTenant } from "./NoTenant";

const EXAMPLE_BOUNDARY =
  "MULTIPOLYGON(((74.0 11.5, 78.6 11.5, 78.6 18.5, 74.0 18.5, 74.0 11.5)))";

export function SupplyChainRoute() {
  const { credential, isConfigured, can } = useSession();
  const manage = can("MANAGE_SUPPLY_CHAIN_REFERENCE_DATA");

  const participants = useResource(() => supplyChain.listParticipants(), [credential], {
    enabled: isConfigured,
  });
  const territories = useResource(() => supplyChain.listTerritories(), [credential], {
    enabled: isConfigured,
  });
  const authorizations = useResource(() => supplyChain.listAuthorizations(), [credential], {
    enabled: isConfigured,
  });

  const [participantForm, setParticipantForm] = useState({
    participant_ref: "",
    name: "",
    role: "DISTRIBUTOR" as ParticipantRole,
  });
  const [territoryForm, setTerritoryForm] = useState({
    territory_ref: "",
    name: "",
    boundary_wkt: EXAMPLE_BOUNDARY,
  });
  const [authorizationForm, setAuthorizationForm] = useState({
    participant_id: "",
    territory_id: "",
  });

  const createParticipant = useAction(async () => {
    await supplyChain.createParticipant({
      participant_ref: participantForm.participant_ref.trim(),
      name: participantForm.name.trim(),
      role: participantForm.role,
    });
    setParticipantForm({ ...participantForm, participant_ref: "", name: "" });
    participants.reload();
  });

  const createTerritory = useAction(async () => {
    await supplyChain.createTerritory({
      territory_ref: territoryForm.territory_ref.trim(),
      name: territoryForm.name.trim(),
      boundary_wkt: territoryForm.boundary_wkt.trim(),
    });
    setTerritoryForm({ ...territoryForm, territory_ref: "", name: "" });
    territories.reload();
  });

  const createAuthorization = useAction(async () => {
    await supplyChain.createAuthorization({
      participant_id: authorizationForm.participant_id,
      territory_id: authorizationForm.territory_id,
      valid_from: new Date(Date.now() - 365 * 86_400_000).toISOString(),
    });
    authorizations.reload();
  });

  const revoke = useAction(async (authorizationId: string) => {
    await supplyChain.revokeAuthorization(authorizationId);
    authorizations.reload();
  });

  if (!isConfigured) return <NoTenant />;

  const participantRows = participants.data ?? [];
  const territoryRows = territories.data ?? [];
  const nameOf = (id: string, rows: { id: string; name: string }[]) =>
    rows.find((row) => row.id === id)?.name ?? id.slice(0, 8);

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Supply chain reference data</h1>
          <p>
            Territories and channel authorizations are what make diversion legible. Until a
            manufacturer has declared at least one authorized territory, no scan can be called
            out of territory — an empty map means unknown, not outside.
          </p>
        </div>
      </div>

      {!manage && (
        <InfoNote>This actor does not hold MANAGE_SUPPLY_CHAIN_REFERENCE_DATA.</InfoNote>
      )}

      <div className="grid-2">
        <Card title="Register a participant">
          <Row>
            <Field label="Reference">
              <input
                value={participantForm.participant_ref}
                onChange={(event) =>
                  setParticipantForm({ ...participantForm, participant_ref: event.target.value })
                }
                placeholder="DIS-KA-01"
              />
            </Field>
            <Field label="Role">
              <select
                value={participantForm.role}
                onChange={(event) =>
                  setParticipantForm({
                    ...participantForm,
                    role: event.target.value as ParticipantRole,
                  })
                }
              >
                {PARTICIPANT_ROLES.map((role) => (
                  <option key={role} value={role}>
                    {role}
                  </option>
                ))}
              </select>
            </Field>
          </Row>
          <Row>
            <Field label="Name">
              <input
                value={participantForm.name}
                onChange={(event) =>
                  setParticipantForm({ ...participantForm, name: event.target.value })
                }
                placeholder="Karnataka distributor"
              />
            </Field>
            <Button
              variant="primary"
              disabled={
                !manage || !participantForm.participant_ref.trim() || !participantForm.name.trim()
              }
              pending={createParticipant.pending}
              onClick={() => void createParticipant.run()}
            >
              Register
            </Button>
          </Row>
          <ErrorNote>{createParticipant.error}</ErrorNote>
        </Card>

        <Card title="Define a territory" subtitle="A real polygon in EPSG:4326, rejected if invalid.">
          <Row>
            <Field label="Reference">
              <input
                value={territoryForm.territory_ref}
                onChange={(event) =>
                  setTerritoryForm({ ...territoryForm, territory_ref: event.target.value })
                }
                placeholder="KA-SOUTH"
              />
            </Field>
            <Field label="Name">
              <input
                value={territoryForm.name}
                onChange={(event) => setTerritoryForm({ ...territoryForm, name: event.target.value })}
                placeholder="Southern Karnataka"
              />
            </Field>
          </Row>
          <Field label="Boundary WKT" hint="MULTIPOLYGON, longitude first.">
            <textarea
              value={territoryForm.boundary_wkt}
              onChange={(event) =>
                setTerritoryForm({ ...territoryForm, boundary_wkt: event.target.value })
              }
            />
          </Field>
          <Button
            variant="primary"
            disabled={!manage || !territoryForm.territory_ref.trim() || !territoryForm.name.trim()}
            pending={createTerritory.pending}
            onClick={() => void createTerritory.run()}
          >
            Define territory
          </Button>
          <ErrorNote>{createTerritory.error}</ErrorNote>
        </Card>

        <Card title="Participants" actions={<Button onClick={participants.reload}>Refresh</Button>}>
          <ErrorNote>{participants.error}</ErrorNote>
          {participants.loading && <Loading />}
          {!participants.loading && participantRows.length === 0 && <Empty>None yet.</Empty>}
          {participantRows.length > 0 && (
            <Table
              head={
                <tr>
                  <th>Reference</th>
                  <th>Name</th>
                  <th>Role</th>
                </tr>
              }
            >
              {participantRows.map((participant) => (
                <tr key={participant.id}>
                  <td>{participant.participant_ref}</td>
                  <td>{participant.name}</td>
                  <td>
                    <Badge tone="neutral">{participant.role}</Badge>
                  </td>
                </tr>
              ))}
            </Table>
          )}
        </Card>

        <Card title="Territories" actions={<Button onClick={territories.reload}>Refresh</Button>}>
          <ErrorNote>{territories.error}</ErrorNote>
          {territories.loading && <Loading />}
          {!territories.loading && territoryRows.length === 0 && <Empty>None yet.</Empty>}
          {territoryRows.length > 0 && (
            <Table
              head={
                <tr>
                  <th>Reference</th>
                  <th>Name</th>
                  <th>Id</th>
                </tr>
              }
            >
              {territoryRows.map((territory) => (
                <tr key={territory.id}>
                  <td>{territory.territory_ref}</td>
                  <td>{territory.name}</td>
                  <td>
                    <Mono value={territory.id} short />
                  </td>
                </tr>
              ))}
            </Table>
          )}
        </Card>

        <Card
          title="Channel authorizations"
          subtitle="Who is allowed to trade where, and from when. A lapsed authorization is an administrative fact, not proof of wrongdoing."
          wide
        >
          <Row>
            <Field label="Participant">
              <select
                value={authorizationForm.participant_id}
                onChange={(event) =>
                  setAuthorizationForm({ ...authorizationForm, participant_id: event.target.value })
                }
              >
                <option value="">Choose</option>
                {participantRows.map((participant) => (
                  <option key={participant.id} value={participant.id}>
                    {participant.participant_ref} ({participant.role})
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Territory">
              <select
                value={authorizationForm.territory_id}
                onChange={(event) =>
                  setAuthorizationForm({ ...authorizationForm, territory_id: event.target.value })
                }
              >
                <option value="">Choose</option>
                {territoryRows.map((territory) => (
                  <option key={territory.id} value={territory.id}>
                    {territory.territory_ref}
                  </option>
                ))}
              </select>
            </Field>
            <Button
              variant="primary"
              disabled={
                !manage || !authorizationForm.participant_id || !authorizationForm.territory_id
              }
              pending={createAuthorization.pending}
              onClick={() => void createAuthorization.run()}
            >
              Grant
            </Button>
          </Row>
          <ErrorNote>{createAuthorization.error ?? revoke.error ?? authorizations.error}</ErrorNote>

          {(authorizations.data ?? []).length === 0 ? (
            <Empty>Nothing authorized yet.</Empty>
          ) : (
            <Table
              head={
                <tr>
                  <th>Participant</th>
                  <th>Territory</th>
                  <th>Valid from</th>
                  <th>Valid until</th>
                  <th />
                </tr>
              }
            >
              {(authorizations.data ?? []).map((authorization) => (
                <tr key={authorization.id}>
                  <td>{nameOf(authorization.participant_id, participantRows)}</td>
                  <td>{nameOf(authorization.territory_id, territoryRows)}</td>
                  <td>
                    <Timestamp value={authorization.valid_from} />
                  </td>
                  <td>
                    {authorization.valid_until ? (
                      <Timestamp value={authorization.valid_until} />
                    ) : (
                      <Badge tone="good">open ended</Badge>
                    )}
                  </td>
                  <td>
                    <Button
                      variant="ghost"
                      disabled={!manage || Boolean(authorization.valid_until)}
                      onClick={() => void revoke.run(authorization.id)}
                    >
                      Revoke
                    </Button>
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
