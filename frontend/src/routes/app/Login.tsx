import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { identity } from "../../api/endpoints";
import { CAPABILITIES } from "../../api/types";
import type { Capability } from "../../api/types";
import {
  Button,
  Card,
  ErrorNote,
  Field,
  InfoNote,
  Row,
  TechnicalDisclosure,
} from "../../components/ui";
import { useAction } from "../../hooks/useResource";
import { runDemoScenario, scenarioFailure } from "../../scenario/demo";
import type { ScenarioLine } from "../../scenario/demo";
import { useSession } from "../../session/SessionContext";

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
                  on ? selected.filter((value) => value !== capability) : [...selected, capability],
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

export function Login() {
  const { session, update } = useSession();
  const navigate = useNavigate();

  const [manufacturerId, setManufacturerId] = useState(session.manufacturerId);
  const [manufacturerName, setManufacturerName] = useState(session.manufacturerName);
  const [actorId, setActorId] = useState(session.actorId || "operator");
  const [newTenantName, setNewTenantName] = useState("");
  const [lines, setLines] = useState<ScenarioLine[]>([]);
  const [scenarioRunning, setScenarioRunning] = useState(false);

  const enter = useAction(async () => {
    update({
      manufacturerId: manufacturerId.trim(),
      manufacturerName: manufacturerName.trim(),
      actorId: actorId.trim(),
      capabilities: [...CAPABILITIES],
    });
    navigate("/app");
  });

  const onboard = useAction(async () => {
    const created = await identity.createManufacturer(newTenantName.trim());
    setManufacturerId(created.id);
    setManufacturerName(created.name);
    setNewTenantName("");
  });

  const seed = useAction(async () => {
    setScenarioRunning(true);
    setLines([]);
    try {
      const outcome = await runDemoScenario((line) => setLines((current) => [...current, line]));
      update({ ...outcome.session, capabilities: [...CAPABILITIES] });
      setLines((current) => [...current, { kind: "done", text: "Scenario complete." }]);
      navigate("/app");
    } catch (cause) {
      setLines((current) => [...current, scenarioFailure(cause)]);
      throw cause;
    } finally {
      setScenarioRunning(false);
    }
  });

  return (
    <div className="stack" style={{ width: "100%", maxWidth: "440px", gap: "var(--space-5)" }}>
      <div className="stack" style={{ gap: "6px", textAlign: "center" }}>
        <h1>Sign in to your workspace</h1>
        <p className="muted">Enter the manufacturer and actor you're operating as.</p>
      </div>

      <Card
        title="Workspace credentials"
        subtitle="Scopes every request on this device to one manufacturer and actor."
      >
        <Field label="Manufacturer id">
          <input
            value={manufacturerId}
            onChange={(event) => setManufacturerId(event.target.value.trim())}
            placeholder="uuid"
          />
        </Field>
        <Field label="Manufacturer name" hint="Display only.">
          <input
            value={manufacturerName}
            onChange={(event) => setManufacturerName(event.target.value)}
            placeholder="Kisan Crop Sciences"
          />
        </Field>
        <Field label="Actor id">
          <input
            value={actorId}
            onChange={(event) => setActorId(event.target.value.trim())}
            placeholder="operator"
          />
        </Field>

        <hr className="rule" />

        <Button
          variant="primary"
          className="button--block"
          disabled={!manufacturerId.trim() || !actorId.trim()}
          pending={enter.pending}
          onClick={() => void enter.run()}
        >
          Enter workspace
        </Button>
        <ErrorNote>{enter.error}</ErrorNote>
      </Card>

      <InfoNote>
        This project uses development credential resolution as a stand-in for authentication.
        The server verifies nothing about who you claim to be, but every capability check that
        follows is real and enforced server-side. A production authentication provider replaces
        this screen in a later milestone.
      </InfoNote>

      <TechnicalDisclosure label="Development tools">
        <div className="stack">
          <div>
            <Field label="Onboard a new manufacturer">
              <Row>
                <input
                  value={newTenantName}
                  onChange={(event) => setNewTenantName(event.target.value)}
                  placeholder="New manufacturer name"
                />
                <Button
                  pending={onboard.pending}
                  disabled={!newTenantName.trim()}
                  onClick={() => void onboard.run()}
                >
                  Onboard
                </Button>
              </Row>
            </Field>
            <ErrorNote>{onboard.error}</ErrorNote>
          </div>

          <Field label="Capabilities for this session">
            <CapabilityPicker
              selected={session.capabilities}
              onChange={(capabilities) => update({ capabilities })}
            />
          </Field>

          <div>
            <Button pending={scenarioRunning} onClick={() => void seed.run()}>
              Seed a demonstration tenant
            </Button>
            {lines.length > 0 && (
              <div className="scenario-log" style={{ marginTop: "var(--space-2)" }}>
                {lines.map((line, index) => (
                  <span key={index} className={`scenario-log__line--${line.kind}`}>
                    {line.kind === "done" ? "\u2713 " : line.kind === "fail" ? "\u2717 " : "\u00b7 "}
                    {line.text}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      </TechnicalDisclosure>
    </div>
  );
}
