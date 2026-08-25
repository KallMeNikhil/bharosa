import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { identity, intelligence } from "../../api/endpoints";
import { AssessmentSummary } from "../../components/Evidence";
import {
  Button,
  Card,
  Empty,
  ErrorNote,
  Field,
  InfoNote,
  Loading,
  Mono,
  PageHeader,
} from "../../components/ui";
import { useAction, useResource } from "../../hooks/useResource";
import { useSession } from "../../session/SessionContext";

export function Risk() {
  const { credential, can } = useSession();
  const identities = useResource(() => identity.listIdentities({ limit: 500 }), [credential]);
  const [selected, setSelected] = useState("");

  const rows = useMemo(() => identities.data ?? [], [identities.data]);
  const matchedIdentity = useMemo(
    () => rows.find((row) => row.id === selected) ?? null,
    [rows, selected],
  );

  const assessments = useResource(
    () => intelligence.listAssessments(selected),
    [credential, selected],
    { enabled: Boolean(selected) },
  );

  const assess = useAction(async () => {
    await intelligence.assessRisk(selected);
    assessments.reload();
  });

  return (
    <>
      <PageHeader
        eyebrow="Intelligence"
        title="Risk"
        description="Bharosa does not expose a single tenant-wide risk feed — confidence is graded per identity, from evidence that is always cited and never a raw score. Look up one identity at a time, the same way an investigator would."
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
          title="Risk assessments"
          subtitle={
            matchedIdentity ? (
              <>
                <Mono value={matchedIdentity.serial} /> —{" "}
                <Link to={`/app/identities/${matchedIdentity.id}`}>full identity detail</Link>
              </>
            ) : undefined
          }
          actions={
            <Button disabled={!can("REVIEW_RISK")} pending={assess.pending} onClick={() => void assess.run()}>
              Assess now
            </Button>
          }
          wide
        >
          <ErrorNote>{assess.error ?? assessments.error}</ErrorNote>
          {assessments.loading && <Loading />}
          {!assessments.loading && (assessments.data ?? []).length === 0 && (
            <Empty>No assessment yet. Detection must produce evidence first.</Empty>
          )}
          {(assessments.data ?? []).map((assessment) => (
            <AssessmentSummary key={assessment.id} assessment={assessment} />
          ))}
        </Card>
      )}

      <InfoNote>
        A single anomalous signal is never sufficient grounds for a conclusion. Confidence here is
        graded evidence, never a claim of certainty.
      </InfoNote>
    </>
  );
}
