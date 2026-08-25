import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { intelligence } from "../../api/endpoints";
import { LEGAL_INCIDENT_TRANSITIONS } from "../../api/types";
import type { IncidentStatus } from "../../api/types";
import { AssessmentSummary, EvidenceList, contributionsByEvidence } from "../../components/Evidence";
import { Badge, Button, Card, Empty, ErrorNote, Field, InfoNote, Loading, Mono, PageHeader, Table, Timestamp } from "../../components/ui";
import { useAction, useResource } from "../../hooks/useResource";
import { useSession } from "../../session/SessionContext";

export function IncidentDetail() {
  const { incidentId = "" } = useParams();
  const { credential, can } = useSession();
  const enabled = Boolean(incidentId);

  const incident = useResource(
    () => intelligence.getInvestigation(incidentId),
    [credential, incidentId],
    { enabled },
  );
  const divergence = useResource(
    () => intelligence.divergence(incidentId),
    [credential, incidentId],
    { enabled },
  );
  const identityId = incident.data?.identity_id ?? "";
  const assessments = useResource(
    () => intelligence.listAssessments(identityId),
    [credential, identityId],
    { enabled: enabled && Boolean(identityId) },
  );

  const [note, setNote] = useState("");

  const move = useAction(async (status: IncidentStatus) => {
    await intelligence.transitionInvestigation(incidentId, status, note || null);
    setNote("");
    incident.reload();
  });

  if (incident.loading) return <Loading />;
  if (incident.error) return <ErrorNote>{incident.error}</ErrorNote>;
  if (!incident.data) return <Empty>Incident not found.</Empty>;

  const detail = incident.data;
  const assessment =
    (assessments.data ?? []).find((row) => row.id === detail.risk_assessment_id) ?? null;
  const contributions = contributionsByEvidence(assessment);
  const nextStatuses = LEGAL_INCIDENT_TRANSITIONS[detail.status];

  return (
    <>
      <PageHeader
        eyebrow="Intelligence"
        title="Incident review"
        description={
          <>
            <Badge>{detail.status}</Badge> opened by {detail.opened_by}{" "}
            <Timestamp value={detail.opened_at} />{" "}
            <Link to={`/app/identities/${detail.identity_id}`}>the identity</Link>
          </>
        }
      />

      <Card title="Summary">
        <p>{detail.summary}</p>
        <InfoNote>
          This is a graded finding for a human reviewer. Nothing here establishes that anyone did
          anything wrong, and each signal below is shown together with its innocent reading.
        </InfoNote>
      </Card>

      {assessment && (
        <Card title="The assessment this incident rests on">
          <AssessmentSummary assessment={assessment} />
        </Card>
      )}

      <Card
        title="Cited evidence"
        subtitle="Every signal appears with both readings, because a screen that shows only the accusatory one defeats the reason the benign explanation is returned at all."
      >
        <EvidenceList evidence={detail.cited_evidence} contributions={contributions} />
      </Card>

      <Card title="Where the route diverged">
        <ErrorNote>{divergence.error}</ErrorNote>
        {divergence.data?.description ? (
          <>
            <p>{divergence.data.description}</p>
            <Table
              head={
                <tr>
                  <th>Expected custodian</th>
                  <th>Observed custodian</th>
                  <th>Event</th>
                </tr>
              }
            >
              <tr>
                <td>{divergence.data.expected_custodian ?? "—"}</td>
                <td>{divergence.data.observed_custodian ?? "—"}</td>
                <td>
                  <Mono value={divergence.data.event_id} short />
                </td>
              </tr>
            </Table>
          </>
        ) : (
          <Empty>No custody divergence was found for this identity.</Empty>
        )}
      </Card>

      <Card title="Case history" subtitle="Append-only. A status is never edited, only added to.">
        <div className="timeline">
          {detail.events.map((event, index, array) => (
            <div className="timeline__item" key={event.sequence}>
              <span className="timeline__rail">
                <span className="timeline__dot timeline__dot--good" />
                {index < array.length - 1 && <span className="timeline__line" />}
              </span>
              <div className="timeline__body">
                <div className="cluster">
                  {event.previous_status && <span className="muted">{event.previous_status} →</span>}
                  <Badge>{event.new_status}</Badge>
                </div>
                {event.note && <p style={{ margin: "4px 0 0" }}>{event.note}</p>}
                <div className="timeline__meta">
                  {event.actor} · <Timestamp value={event.occurred_at} />
                </div>
              </div>
            </div>
          ))}
        </div>
      </Card>

      <Card title="Move this case on">
        {nextStatuses.length === 0 ? (
          <InfoNote>{detail.status} is final.</InfoNote>
        ) : (
          <>
            <Field label="Note">
              <textarea
                value={note}
                onChange={(event) => setNote(event.target.value)}
                placeholder="What changed your reading of this case."
              />
            </Field>
            <div className="button-row">
              {nextStatuses.map((status) => (
                <Button
                  key={status}
                  variant={status === "DISMISSED" ? "secondary" : "primary"}
                  disabled={!can("MANAGE_INVESTIGATION")}
                  pending={move.pending}
                  onClick={() => void move.run(status)}
                >
                  {status}
                </Button>
              ))}
            </div>
          </>
        )}
        <ErrorNote>{move.error}</ErrorNote>
      </Card>
    </>
  );
}
