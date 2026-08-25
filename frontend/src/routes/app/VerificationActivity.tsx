import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { identity, intelligence } from "../../api/endpoints";
import {
  Badge,
  Card,
  Empty,
  ErrorNote,
  Field,
  InfoNote,
  Loading,
  Mono,
  PageHeader,
  Timestamp,
} from "../../components/ui";
import { useResource } from "../../hooks/useResource";
import { useSession } from "../../session/SessionContext";

export function VerificationActivity() {
  const { credential } = useSession();
  const identities = useResource(() => identity.listIdentities({ limit: 500 }), [credential]);
  const [selected, setSelected] = useState("");

  const rows = useMemo(() => identities.data ?? [], [identities.data]);
  const matchedIdentity = useMemo(
    () => rows.find((row) => row.id === selected) ?? null,
    [rows, selected],
  );

  const events = useResource(
    () => intelligence.verificationEvents(selected),
    [credential, selected],
    { enabled: Boolean(selected) },
  );

  return (
    <>
      <PageHeader
        eyebrow="Trust & verification"
        title="Verification activity"
        description="Bharosa does not expose a single feed of every scan across a manufacturer's entire catalogue — look up one identity at a time, the same way a field investigator would."
      />

      <Card title="Look up an identity">
        <Field label="Identity" hint="Choose from identities reserved by this manufacturer.">
          <select value={selected} onChange={(event) => setSelected(event.target.value)}>
            <option value="">Choose an identity</option>
            {rows.map((row) => (
              <option key={row.id} value={row.id}>
                {row.serial} — {row.lifecycle_state}
              </option>
            ))}
          </select>
        </Field>
        <ErrorNote>{identities.error}</ErrorNote>
      </Card>

      {selected && (
        <Card
          title="Verification history"
          subtitle={
            matchedIdentity ? (
              <>
                <Mono value={matchedIdentity.serial} /> —{" "}
                <Link to={`/app/identities/${matchedIdentity.id}`}>full identity detail</Link>
              </>
            ) : undefined
          }
          wide
        >
          <ErrorNote>{events.error}</ErrorNote>
          {events.loading && <Loading />}
          {!events.loading && (events.data ?? []).length === 0 && (
            <Empty>No verification events recorded for this identity yet.</Empty>
          )}
          {(events.data ?? []).length > 0 && (
            <div className="timeline">
              {(events.data ?? []).map((event, index, array) => {
                const tone = event.state === "GENUINE" ? "good" : event.state === "CAUTION" ? "warn" : "bad";
                return (
                  <div className="timeline__item" key={event.id}>
                    <span className="timeline__rail">
                      <span className={`timeline__dot timeline__dot--${tone}`} />
                      {index < array.length - 1 && <span className="timeline__line" />}
                    </span>
                    <div className="timeline__body">
                      <div className="cluster">
                        <Badge tone={tone}>{event.state}</Badge>
                        <span className="muted">via {event.channel}</span>
                      </div>
                      <div className="timeline__meta">
                        <Timestamp value={event.occurred_at} /> · signature{" "}
                        {event.signature_valid ? "valid" : "invalid"} · lifecycle was{" "}
                        {event.lifecycle_state_at_scan}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </Card>
      )}

      <InfoNote>
        A repeated scan of a legitimate identity is normal, expected data — never automatically
        treated as suspicious.
      </InfoNote>
    </>
  );
}
