import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { ApiError } from "../../api/client";
import { auth, identity } from "../../api/endpoints";
import { CAPABILITIES } from "../../api/types";
import type { Capability } from "../../api/types";
import {
  Button,
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
import { useStartSession } from "../../session/useAccountSession";

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
  const startSession = useStartSession();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const signIn = useAction(async () => {
    await startSession(await auth.signIn({ email: email.trim(), password }));
  });

  return (
    <div className="auth-form">
      <div className="auth-form__intro">
        <h1>Sign in to your workspace</h1>
        <p className="muted">Use the email and password your company's account was created with.</p>
      </div>

      <form
        className="card"
        onSubmit={(event) => {
          event.preventDefault();
          if (email.trim() && password && !signIn.pending) void signIn.run();
        }}
      >
        <div className="card__body">
          <Field label="Email">
            <input
              type="email"
              autoComplete="username"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="you@company.com"
            />
          </Field>
          <Field label="Password">
            <input
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </Field>
          <Button
            type="submit"
            variant="primary"
            className="button--block"
            disabled={!email.trim() || !password}
            pending={signIn.pending}
          >
            Sign in
          </Button>
          <ErrorNote>{signIn.error}</ErrorNote>
        </div>
      </form>

      <p className="auth-form__switch">
        New to Bharosa? <Link to="/app/register">Create your company's account</Link>
      </p>

      {import.meta.env.DEV && <DevelopmentTools />}
    </div>
  );
}

function DevelopmentTools() {
  const { session, update } = useSession();
  const navigate = useNavigate();

  const [manufacturerId, setManufacturerId] = useState(session.manufacturerId);
  const [actorId, setActorId] = useState(session.actorId || "operator");
  const [newTenantName, setNewTenantName] = useState("");
  const [lines, setLines] = useState<ScenarioLine[]>([]);
  const [scenarioRunning, setScenarioRunning] = useState(false);

  const enter = useAction(async () => {
    let found;
    try {
      found = await identity.ownManufacturer(`dev:${manufacturerId.trim()}:${actorId.trim()}:*`);
    } catch (cause) {
      if (cause instanceof ApiError && (cause.status === 404 || cause.status === 401)) {
        throw new Error("No manufacturer exists with this id. Onboard one or seed a demonstration tenant.");
      }
      throw cause;
    }
    update({
      token: "",
      manufacturerId: found.id,
      manufacturerName: found.name,
      actorId: actorId.trim(),
      capabilities: [...CAPABILITIES],
    });
    navigate("/app");
  });

  const onboard = useAction(async () => {
    const created = await identity.createManufacturer(newTenantName.trim());
    setManufacturerId(created.id);
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
    <TechnicalDisclosure label="Development tools">
      <div className="stack">
        <InfoNote>
          Development builds only. These act as any manufacturer without an account and are not
          part of the public site.
        </InfoNote>
        <Row>
          <Field label="Manufacturer id">
            <input
              value={manufacturerId}
              onChange={(event) => setManufacturerId(event.target.value.trim())}
              placeholder="uuid"
            />
          </Field>
          <Field label="Actor id">
            <input
              value={actorId}
              onChange={(event) => setActorId(event.target.value.trim())}
              placeholder="operator"
            />
          </Field>
        </Row>
        <Button
          disabled={!manufacturerId.trim() || !actorId.trim()}
          pending={enter.pending}
          onClick={() => void enter.run()}
        >
          Enter as this manufacturer
        </Button>
        <ErrorNote>{enter.error}</ErrorNote>

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
            <div className="scenario-log auth-form__log">
              {lines.map((line, index) => (
                <span key={index} className={`scenario-log__line--${line.kind}`}>
                  {line.kind === "done" ? "✓ " : line.kind === "fail" ? "✗ " : "· "}
                  {line.text}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </TechnicalDisclosure>
  );
}
