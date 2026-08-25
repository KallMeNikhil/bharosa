import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { identity, intelligence, supplyChain } from "../../api/endpoints";
import { LEGAL_TRANSITIONS, LIFECYCLE_PATH, SUPPLY_CHAIN_EVENT_TYPES } from "../../api/types";
import type { LifecycleState, SupplyChainEventType } from "../../api/types";
import { AssessmentSummary, EvidenceList, contributionsByEvidence } from "../../components/Evidence";
import { Badge, Button, Card, Empty, ErrorNote, Field, InfoNote, Loading, Mono, Row, Table, Timestamp } from "../../components/ui";
import { useAction, useResource } from "../../hooks/useResource";
import { recallKeyHandle } from "../../session/keyHandles";
import { useSession } from "../../session/SessionContext";
import { NoTenant } from "./NoTenant";

function Pipeline({ state }: { state: LifecycleState }) {
  if (state === "PRINT_REJECTED") {
    return (
      <div className="pipeline">
        <span className="pipeline__step is-current">PRINT_REJECTED</span>
      </div>
    );
  }
  const reached = LIFECYCLE_PATH.indexOf(state);
  return (
    <div className="pipeline">
      {LIFECYCLE_PATH.map((step, index) => (
        <span key={step}>
          {index > 0 && <span className="pipeline__arrow">→ </span>}
          <span
            className={`pipeline__step${
              index < reached ? " is-done" : index === reached ? " is-current" : ""
            }`}
          >
            {step}
          </span>
        </span>
      ))}
    </div>
  );
}

export function IdentityDetail() {
  const { identityId = "" } = useParams();
  const { credential, isConfigured, can } = useSession();
  const navigate = useNavigate();

  const enabled = isConfigured && Boolean(identityId);
  const subject = useResource(() => identity.getIdentity(identityId), [credential, identityId], {
    enabled,
  });
  const events = useResource(() => identity.identityEvents(identityId), [credential, identityId], {
    enabled,
  });
  const keys = useResource(() => identity.listKeys(), [credential], { enabled });
  const custody = useResource(
    () => supplyChain.identityEvents(identityId),
    [credential, identityId],
    { enabled },
  );
  const custodian = useResource(
    () => supplyChain.custodian(identityId),
    [credential, identityId],
    { enabled },
  );
  const participants = useResource(() => supplyChain.listParticipants(), [credential], { enabled });
  const scans = useResource(
    () => intelligence.verificationEvents(identityId),
    [credential, identityId],
    { enabled },
  );
  const evidence = useResource(
    () => intelligence.listEvidence(identityId),
    [credential, identityId],
    { enabled },
  );
  const assessments = useResource(
    () => intelligence.listAssessments(identityId),
    [credential, identityId],
    { enabled },
  );
  const incidents = useResource(
    () => intelligence.listInvestigations(identityId),
    [credential, identityId],
    { enabled },
  );

  const [signingKeyId, setSigningKeyId] = useState("");
  const [keyHandle, setKeyHandle] = useState("");
  const [digitalLink, setDigitalLink] = useState<string | null>(null);
  const [eventForm, setEventForm] = useState({
    event_type: "DISPATCH" as SupplyChainEventType,
    source_participant_id: "",
    destination_participant_id: "",
    reason: "",
    occurred_at: new Date().toISOString().slice(0, 16),
  });
  const [citedEvidence, setCitedEvidence] = useState<string[]>([]);
  const [summary, setSummary] = useState("");

  const reloadIdentity = () => {
    subject.reload();
    events.reload();
  };

  const sign = useAction(async () => {
    await identity.signIdentity(identityId, {
      manufacturer_key_id: signingKeyId,
      key_handle: keyHandle,
    });
    reloadIdentity();
  });

  const transition = useAction(async (next: LifecycleState) => {
    await identity.transitionIdentity(identityId, next);
    reloadIdentity();
  });

  const fetchLink = useAction(async () => {
    const link = await identity.digitalLink(identityId);
    setDigitalLink(link.uri);
  });

  const recordEvent = useAction(async () => {
    await supplyChain.recordEvent({
      identity_id: identityId,
      event_type: eventForm.event_type,
      occurred_at: new Date(eventForm.occurred_at).toISOString(),
      source_participant_id: eventForm.source_participant_id || null,
      destination_participant_id: eventForm.destination_participant_id || null,
      reason: eventForm.reason || null,
    });
    custody.reload();
    custodian.reload();
  });

  const detect = useAction(async () => {
    await intelligence.runDetection(identityId);
    evidence.reload();
  });

  const assess = useAction(async () => {
    await intelligence.assessRisk(identityId);
    assessments.reload();
  });

  const investigate = useAction(async () => {
    const latest = (assessments.data ?? [])[0];
    const incident = await intelligence.openInvestigation({
      risk_assessment_id: latest.id,
      evidence_ids: citedEvidence,
      summary: summary.trim(),
    });
    navigate(`/investigations/${incident.id}`);
  });

  if (!isConfigured) return <NoTenant />;
  if (subject.loading) return <Loading />;
  if (subject.error) return <ErrorNote>{subject.error}</ErrorNote>;
  if (!subject.data) return <Empty>Identity not found.</Empty>;

  const row = subject.data;
  const activeKeys = (keys.data ?? []).filter((key) => key.status === "ACTIVE");
  const nextStates = LEGAL_TRANSITIONS[row.lifecycle_state];
  const participantName = (participantId: string | null) => {
    if (!participantId) return "—";
    const match = (participants.data ?? []).find((item) => item.id === participantId);
    return match ? `${match.participant_ref} (${match.role})` : participantId.slice(0, 8);
  };
  const latestAssessment = (assessments.data ?? [])[0] ?? null;
  const contributions = contributionsByEvidence(latestAssessment);

  return (
    <>
      <div className="page-head">
        <div>
          <h1>
            <Mono value={row.serial} />
          </h1>
          <p>
            <Badge>{row.lifecycle_state}</Badge> · created <Timestamp value={row.created_at} /> ·{" "}
            <Link to={`/identities?batch=${row.batch_id}`}>batch</Link>
          </p>
        </div>
      </div>

      <Card title="Lifecycle">
        <Pipeline state={row.lifecycle_state} />

        {row.lifecycle_state === "RESERVED" && (
          <>
            <Row>
              <Field label="Signing key">
                <select
                  value={signingKeyId}
                  onChange={(event) => {
                    setSigningKeyId(event.target.value);
                    setKeyHandle(recallKeyHandle(event.target.value));
                  }}
                >
                  <option value="">Choose an ACTIVE key</option>
                  {activeKeys.map((key) => (
                    <option key={key.id} value={key.id}>
                      version {key.key_version}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Key handle">
                <input
                  value={keyHandle}
                  onChange={(event) => setKeyHandle(event.target.value)}
                  placeholder="handle returned by POST /keys"
                />
              </Field>
              <Button
                variant="primary"
                disabled={!can("AUTHORIZE_SIGNING") || !signingKeyId || !keyHandle}
                pending={sign.pending}
                onClick={() => void sign.run()}
              >
                Sign
              </Button>
            </Row>
            <ErrorNote>{sign.error}</ErrorNote>
          </>
        )}

        {nextStates.length > 0 && (
          <div className="button-row">
            {nextStates.map((next) => (
              <Button key={next} pending={transition.pending} onClick={() => void transition.run(next)}>
                Move to {next}
              </Button>
            ))}
          </div>
        )}
        {nextStates.length === 0 && row.lifecycle_state !== "RESERVED" && (
          <InfoNote>{row.lifecycle_state} is a terminal state.</InfoNote>
        )}
        <ErrorNote>{transition.error}</ErrorNote>

        <Row>
          <Button pending={fetchLink.pending} onClick={() => void fetchLink.run()}>
            Build GS1 Digital Link
          </Button>
          {digitalLink && <Mono value={digitalLink} />}
        </Row>
        <ErrorNote>{fetchLink.error}</ErrorNote>
      </Card>

      <div className="grid-2">
        <Card title="Issuance events" subtitle="Append-only, hash-chained per identity." wide>
          <ErrorNote>{events.error}</ErrorNote>
          {(events.data ?? []).length === 0 ? (
            <Empty>No issuance events.</Empty>
          ) : (
            <Table
              head={
                <tr>
                  <th>#</th>
                  <th>Type</th>
                  <th>From</th>
                  <th>To</th>
                  <th>Actor</th>
                  <th>When</th>
                </tr>
              }
            >
              {(events.data ?? []).map((event) => (
                <tr key={event.sequence}>
                  <td>{event.sequence}</td>
                  <td>{event.event_type}</td>
                  <td>{event.previous_state ?? <span className="muted">—</span>}</td>
                  <td>
                    <Badge>{event.new_state}</Badge>
                  </td>
                  <td>{event.actor ?? <span className="muted">—</span>}</td>
                  <td>
                    <Timestamp value={event.occurred_at} />
                  </td>
                </tr>
              ))}
            </Table>
          )}
        </Card>

        <Card
          title="Custody"
          subtitle="The current custodian is recomputed from the event log on every request; nothing stores it."
          actions={
            <Button
              onClick={() => {
                custody.reload();
                custodian.reload();
              }}
            >
              Refresh
            </Button>
          }
          wide
        >
          <InfoNote>
            Currently held by <strong>{participantName(custodian.data?.custodian_id ?? null)}</strong>
          </InfoNote>

          <Row>
            <Field label="Event type">
              <select
                value={eventForm.event_type}
                onChange={(event) =>
                  setEventForm({
                    ...eventForm,
                    event_type: event.target.value as SupplyChainEventType,
                  })
                }
              >
                {SUPPLY_CHAIN_EVENT_TYPES.map((type) => (
                  <option key={type} value={type}>
                    {type}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Source">
              <select
                value={eventForm.source_participant_id}
                onChange={(event) =>
                  setEventForm({ ...eventForm, source_participant_id: event.target.value })
                }
              >
                <option value="">None</option>
                {(participants.data ?? []).map((participant) => (
                  <option key={participant.id} value={participant.id}>
                    {participant.participant_ref} ({participant.role})
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Destination">
              <select
                value={eventForm.destination_participant_id}
                onChange={(event) =>
                  setEventForm({ ...eventForm, destination_participant_id: event.target.value })
                }
              >
                <option value="">None</option>
                {(participants.data ?? []).map((participant) => (
                  <option key={participant.id} value={participant.id}>
                    {participant.participant_ref} ({participant.role})
                  </option>
                ))}
              </select>
            </Field>
          </Row>
          <Row>
            <Field label="Occurred at">
              <input
                type="datetime-local"
                value={eventForm.occurred_at}
                onChange={(event) => setEventForm({ ...eventForm, occurred_at: event.target.value })}
              />
            </Field>
            <Field label="Reason" hint="Required for CUSTODY_ADJUSTMENT.">
              <input
                value={eventForm.reason}
                onChange={(event) => setEventForm({ ...eventForm, reason: event.target.value })}
              />
            </Field>
            <Button
              variant="primary"
              disabled={!can("RECORD_SUPPLY_CHAIN_EVENT")}
              pending={recordEvent.pending}
              onClick={() => void recordEvent.run()}
            >
              Record event
            </Button>
          </Row>
          <ErrorNote>{recordEvent.error ?? custody.error}</ErrorNote>

          {(custody.data ?? []).length === 0 ? (
            <Empty>No custody events yet.</Empty>
          ) : (
            <Table
              head={
                <tr>
                  <th>#</th>
                  <th>Type</th>
                  <th>From</th>
                  <th>To</th>
                  <th>Reason</th>
                  <th>When</th>
                </tr>
              }
            >
              {(custody.data ?? []).map((event) => (
                <tr key={event.id}>
                  <td>{event.sequence}</td>
                  <td>
                    <Badge tone="neutral">{event.event_type}</Badge>
                  </td>
                  <td>{participantName(event.source_participant_id)}</td>
                  <td>{participantName(event.destination_participant_id)}</td>
                  <td>{event.reason ?? <span className="muted">—</span>}</td>
                  <td>
                    <Timestamp value={event.occurred_at} />
                  </td>
                </tr>
              ))}
            </Table>
          )}
        </Card>

        <Card
          title="Verification events"
          subtitle="Written by the public endpoint. Location is stored coarsely; the exact point is never shown back to a consumer."
          actions={<Button onClick={scans.reload}>Refresh</Button>}
          wide
        >
          <ErrorNote>{scans.error}</ErrorNote>
          {(scans.data ?? []).length === 0 ? (
            <Empty>This identity has never been scanned.</Empty>
          ) : (
            <Table
              head={
                <tr>
                  <th>#</th>
                  <th>Answer</th>
                  <th>Channel</th>
                  <th>Signature</th>
                  <th>State at scan</th>
                  <th>Locality</th>
                  <th>When</th>
                </tr>
              }
            >
              {(scans.data ?? []).map((scan) => (
                <tr key={scan.id}>
                  <td>{scan.sequence}</td>
                  <td>
                    <Badge>{scan.state}</Badge>
                  </td>
                  <td>{scan.channel}</td>
                  <td>
                    {scan.signature_valid ? (
                      <Badge tone="good">valid</Badge>
                    ) : (
                      <Badge tone="bad">invalid</Badge>
                    )}
                  </td>
                  <td>{scan.lifecycle_state_at_scan}</td>
                  <td>
                    {scan.coarse_cell ? <Mono value={scan.coarse_cell} /> : <span className="muted">withheld</span>}
                  </td>
                  <td>
                    <Timestamp value={scan.occurred_at} />
                  </td>
                </tr>
              ))}
            </Table>
          )}
        </Card>

        <Card
          title="Detection evidence"
          subtitle="Every signal cites the events it was derived from, and a detector change produces new evidence rather than reinterpreting old evidence."
          actions={
            <Button
              variant="primary"
              disabled={!can("RUN_DETECTION")}
              pending={detect.pending}
              onClick={() => void detect.run()}
            >
              Run detection
            </Button>
          }
          wide
        >
          <ErrorNote>{detect.error ?? evidence.error}</ErrorNote>
          <EvidenceList
            evidence={evidence.data ?? []}
            contributions={contributions}
            selectable
            selected={citedEvidence}
            onToggle={(id) =>
              setCitedEvidence((current) =>
                current.includes(id) ? current.filter((value) => value !== id) : [...current, id],
              )
            }
          />
        </Card>

        <Card
          title="Risk assessments"
          subtitle="Confidence is graded, never certain. Each assessment is appended; none is ever rewritten."
          actions={
            <Button
              disabled={!can("REVIEW_RISK")}
              pending={assess.pending}
              onClick={() => void assess.run()}
            >
              Assess now
            </Button>
          }
          wide
        >
          <ErrorNote>{assess.error ?? assessments.error}</ErrorNote>
          {(assessments.data ?? []).length === 0 ? (
            <Empty>No assessment yet. Detection must produce evidence first.</Empty>
          ) : (
            (assessments.data ?? []).map((assessment) => (
              <AssessmentSummary key={assessment.id} assessment={assessment} />
            ))
          )}
        </Card>

        <Card
          title="Open an investigation"
          subtitle="An incident is the point at which the platform asserts something about a real business, so it cannot be created without citing the evidence it rests on."
          wide
        >
          {(incidents.data ?? []).length > 0 && (
            <InfoNote>
              Already under investigation:{" "}
              {(incidents.data ?? []).map((incident) => (
                <Link key={incident.id} to={`/investigations/${incident.id}`}>
                  {incident.status}{" "}
                </Link>
              ))}
            </InfoNote>
          )}
          <Field label="Summary">
            <textarea
              value={summary}
              onChange={(event) => setSummary(event.target.value)}
              placeholder="What was observed, and why it warrants review."
            />
          </Field>
          <InfoNote>
            {citedEvidence.length} evidence records selected above. Selecting none is rejected by
            the API and again by the database at commit time.
          </InfoNote>
          <Button
            variant="primary"
            disabled={
              !can("MANAGE_INVESTIGATION") ||
              !latestAssessment ||
              citedEvidence.length === 0 ||
              !summary.trim()
            }
            pending={investigate.pending}
            onClick={() => void investigate.run()}
          >
            Open incident
          </Button>
          <ErrorNote>{investigate.error}</ErrorNote>
        </Card>
      </div>
    </>
  );
}
