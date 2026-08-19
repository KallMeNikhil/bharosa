import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { identity } from "../api/endpoints";
import { CAPABILITIES } from "../api/types";
import type { Capability } from "../api/types";
import { Button, Card, ErrorNote, Field, InfoNote, Mono, Row } from "../components/ui";
import { useAction, useResource } from "../hooks/useResource";
import { runDemoScenario, scenarioFailure } from "../scenario/demo";
import type { ScenarioLine } from "../scenario/demo";
import { useSession } from "../session/SessionContext";

function CapabilityPicker({
  selected,
  onChange,
}: {
  selected: Capability[];
  onChange: (next: Capability[]) => void;
}) {
  return (
    <div className="capability-picker">
      {CAPABILITIES.map((capability) => {
        const on = selected.includes(capability);
        return (
          <label key={capability} className={`capability-chip${on ? " is-on" : ""}`}>
            <input
              type="checkbox"
              checked={on}
              onChange={() =>
                onChange(
                  on
                    ? selected.filter((value) => value !== capability)
                    : [...selected, capability],
                )
              }
            />
            {capability}
          </label>
        );
      })}
    </div>
  );
}

export function SessionRoute() {
  const { session, credential, isConfigured, update, reset } = useSession();
  const navigate = useNavigate();

  const [newTenantName, setNewTenantName] = useState("");
  const [lines, setLines] = useState<ScenarioLine[]>([]);
  const [scenarioRunning, setScenarioRunning] = useState(false);

  const whoami = useResource(() => identity.me(), [credential], { enabled: isConfigured });

  const onboard = useAction(async () => {
    const created = await identity.createManufacturer(newTenantName.trim());
    update({
      manufacturerId: created.id,
      manufacturerName: created.name,
      actorId: session.actorId || "operator",
      capabilities: [...CAPABILITIES],
    });
    setNewTenantName("");
  });

  const seed = useAction(async () => {
    setScenarioRunning(true);
    setLines([]);
    try {
      const outcome = await runDemoScenario((line) => setLines((current) => [...current, line]));
      update({ ...outcome.session, capabilities: [...CAPABILITIES] });
      setLines((current) => [
        ...current,
        { kind: "done", text: "Scenario complete. Opening the diverted pack." },
      ]);
      navigate(`/identities/${outcome.divertedIdentityId}`);
    } catch (cause) {
      setLines((current) => [...current, scenarioFailure(cause)]);
      throw cause;
    } finally {
      setScenarioRunning(false);
    }
  });

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Tenant and actor</h1>
          <p>
            Every internal request carries a development credential naming a manufacturer, an
            actor and that actor&apos;s capabilities. This is a stand-in for authentication, not
            authentication: the server reads the actor straight out of the credential and
            verifies nothing. Capability enforcement, however, is real and happens server-side.
          </p>
        </div>
      </div>

      <div className="grid-2">
        <Card
          title="Seed a demonstration tenant"
          subtitle="Runs the whole platform end to end through the public API: production, custody, four scans of a diverted pack, detection, risk and an investigation."
        >
          <Button
            variant="primary"
            pending={scenarioRunning}
            onClick={() => void seed.run()}
            disabled={scenarioRunning}
          >
            Run the full scenario
          </Button>
          <ErrorNote>{seed.error}</ErrorNote>
          {lines.length > 0 && (
            <div className="scenario-log">
              {lines.map((line, index) => (
                <span key={index} className={`scenario-log__line--${line.kind}`}>
                  {line.kind === "done" ? "✓ " : line.kind === "fail" ? "✗ " : "· "}
                  {line.text}
                </span>
              ))}
            </div>
          )}
        </Card>

        <Card
          title="Onboard an empty manufacturer"
          subtitle="Available outside production only. Onboarding happens before any tenant scope for the new manufacturer can exist, so it takes no credential."
        >
          <Row>
            <Field label="Manufacturer name">
              <input
                value={newTenantName}
                onChange={(event) => setNewTenantName(event.target.value)}
                placeholder="Kisan Crop Sciences"
              />
            </Field>
            <Button
              variant="primary"
              pending={onboard.pending}
              disabled={!newTenantName.trim()}
              onClick={() => void onboard.run()}
            >
              Onboard
            </Button>
          </Row>
          <ErrorNote>{onboard.error}</ErrorNote>
        </Card>

        <Card title="Current credential" wide>
          <Row>
            <Field label="Manufacturer id">
              <input
                value={session.manufacturerId}
                onChange={(event) => update({ manufacturerId: event.target.value.trim() })}
                placeholder="uuid"
              />
            </Field>
            <Field label="Manufacturer name" hint="Display only; never sent to the API.">
              <input
                value={session.manufacturerName}
                onChange={(event) => update({ manufacturerName: event.target.value })}
              />
            </Field>
            <Field label="Actor id">
              <input
                value={session.actorId}
                onChange={(event) => update({ actorId: event.target.value.trim() })}
                placeholder="operator"
              />
            </Field>
          </Row>

          <Field label="Capabilities">
            <CapabilityPicker
              selected={session.capabilities}
              onChange={(capabilities) => update({ capabilities })}
            />
          </Field>

          <Row>
            <Button onClick={() => update({ capabilities: [...CAPABILITIES] })}>
              Grant everything
            </Button>
            <Button onClick={() => update({ capabilities: [] })}>Revoke everything</Button>
            <Button variant="danger" onClick={reset}>
              Clear session
            </Button>
          </Row>

          {credential ? (
            <Field label="Authorization header">
              <Mono value={`Bearer ${credential}`} />
            </Field>
          ) : (
            <InfoNote>
              A manufacturer id and an actor id are both required before any internal endpoint
              will answer.
            </InfoNote>
          )}
        </Card>

        <Card
          title="What the server thinks you are"
          subtitle="GET /me, resolved from the credential above."
          actions={<Button onClick={whoami.reload}>Refresh</Button>}
          wide
        >
          {!isConfigured && <InfoNote>Set a credential first.</InfoNote>}
          <ErrorNote>{whoami.error}</ErrorNote>
          {whoami.data && (
            <pre className="scenario-log">{JSON.stringify(whoami.data, null, 2)}</pre>
          )}
        </Card>
      </div>
    </>
  );
}
