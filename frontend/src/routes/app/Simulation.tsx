import { useState } from "react";
import { Link } from "react-router-dom";

import { simulation } from "../../api/endpoints";
import type { ScenarioType, SimulationRunDetailView } from "../../api/types";
import {
  Badge,
  Button,
  Card,
  Empty,
  ErrorNote,
  Field,
  Loading,
  Mono,
  PageHeader,
  Row,
  Stat,
  Table,
  Timestamp,
} from "../../components/ui";
import { useAction, useResource } from "../../hooks/useResource";
import { useSession } from "../../session/SessionContext";

function formatRate(value: number | null): string {
  return value === null ? "—" : `${(value * 100).toFixed(0)}%`;
}

function DetectorBreakdown({ run }: { run: SimulationRunDetailView }) {
  const breakdown = run.latest_evaluation?.per_detector_breakdown ?? {};
  const detectors = Object.keys(breakdown);
  if (detectors.length === 0) return <Empty>No detector fired for this run.</Empty>;
  return (
    <Table
      head={
        <tr>
          <th>Detector</th>
          <th>Signal type</th>
          <th>Count</th>
        </tr>
      }
    >
      {detectors.flatMap((detectorId) =>
        Object.entries(breakdown[detectorId]).map(([signalType, count]) => (
          <tr key={`${detectorId}-${signalType}`}>
            <td>{detectorId}</td>
            <td>{signalType}</td>
            <td>{count}</td>
          </tr>
        )),
      )}
    </Table>
  );
}

function RunResult({
  run,
  onRecompute,
}: {
  run: SimulationRunDetailView;
  onRecompute: () => void;
}) {
  const evaluation = run.latest_evaluation;
  const recompute = useAction(async () => {
    await simulation.recomputeEvaluation(run.id);
    onRecompute();
  });

  return (
    <Card
      title={`Run ${run.id.slice(0, 8)} — ${run.scenario_type}`}
      subtitle={`Seed ${run.seed}, ${run.identity_count} identities`}
      actions={
        <Button pending={recompute.pending} onClick={() => void recompute.run()}>
          Recompute evaluation
        </Button>
      }
    >
      <ErrorNote>{recompute.error}</ErrorNote>
      <Row>
        <Badge>{run.status}</Badge>
        {run.error_message && <span>{run.error_message}</span>}
      </Row>

      {evaluation && (
        <>
          <div className="confusion-matrix">
            <div className="stat stat--good">
              <span className="stat__label">Predicted fraud · actually fraud</span>
              <span className="stat__value">{evaluation.true_positive_count}</span>
              <span className="muted" style={{ fontSize: "0.72rem" }}>
                True positive
              </span>
            </div>
            <div className="stat stat--bad">
              <span className="stat__label">Predicted fraud · actually clean</span>
              <span className="stat__value">{evaluation.false_positive_count}</span>
              <span className="muted" style={{ fontSize: "0.72rem" }}>
                False positive
              </span>
            </div>
            <div className="stat stat--bad">
              <span className="stat__label">Predicted clean · actually fraud</span>
              <span className="stat__value">{evaluation.false_negative_count}</span>
              <span className="muted" style={{ fontSize: "0.72rem" }}>
                False negative — missed fraud
              </span>
            </div>
            <div className="stat stat--good">
              <span className="stat__label">Predicted clean · actually clean</span>
              <span className="stat__value">{evaluation.true_negative_count}</span>
              <span className="muted" style={{ fontSize: "0.72rem" }}>
                True negative
              </span>
            </div>
          </div>
          <Row>
            <Stat label="Precision" value={formatRate(evaluation.precision)} />
            <Stat label="Recall / detection rate" value={formatRate(evaluation.recall)} />
            <Stat label="Missed-fraud rate" value={formatRate(evaluation.missed_fraud_rate)} tone="bad" />
            <Stat
              label="Investigation TP / FP"
              value={`${evaluation.investigation_true_positive_count} / ${evaluation.investigation_false_positive_count}`}
            />
          </Row>
          <DetectorBreakdown run={run} />
        </>
      )}

      <Table
        head={
          <tr>
            <th>Identity</th>
            <th>Ground truth</th>
            <th>Injection</th>
            <th>Expected signals</th>
          </tr>
        }
      >
        {run.ground_truth.map((entry) => (
          <tr key={entry.id}>
            <td>
              <Link to={`/app/identities/${entry.identity_id}`}>
                <Mono value={entry.identity_id} short />
              </Link>
            </td>
            <td>
              <Badge tone={entry.classification === "INJECTED_FRAUD" ? "bad" : "good"}>
                {entry.classification}
              </Badge>
            </td>
            <td>{entry.injection_type ?? "—"}</td>
            <td>{entry.expected_signal_types || "—"}</td>
          </tr>
        ))}
      </Table>
    </Card>
  );
}

export function Simulation() {
  const { credential, can } = useSession();
  const runSimulation = can("RUN_SIMULATION");

  const catalogue = useResource(() => simulation.catalogue(), []);
  const runs = useResource(() => simulation.list(), [credential]);

  const [scenarioType, setScenarioType] = useState<ScenarioType>("LEGITIMATE_BASELINE");
  const [identityCount, setIdentityCount] = useState(6);
  const [seed, setSeed] = useState("");
  const [selectedRun, setSelectedRun] = useState<SimulationRunDetailView | null>(null);

  const create = useAction(async () => {
    const result = await simulation.create({
      scenario_type: scenarioType,
      seed: seed.trim() === "" ? null : Number(seed),
      identity_count: identityCount,
    });
    setSelectedRun(result);
    runs.reload();
  });

  const openRun = useAction(async (runId: string) => {
    const detail = await simulation.get(runId);
    setSelectedRun(detail);
  });

  const scenarios = catalogue.data ?? [];
  const rows = runs.data ?? [];

  return (
    <>
      <PageHeader
        eyebrow="Simulation"
        title="Simulation"
        description="Runs a deterministic synthetic scenario through the real verification, detection, risk and investigation pipeline, then compares the result against ground truth the simulator recorded independently, before any detector ran."
      />

      <Card
        title="Run a scenario"
        subtitle="Ground truth is generated first and never adjusted to match what the detectors find afterwards."
      >
        <Row>
          <Field label="Scenario">
            <select
              value={scenarioType}
              onChange={(event) => setScenarioType(event.target.value as ScenarioType)}
            >
              {scenarios.map((entry) => (
                <option key={entry.scenario_type} value={entry.scenario_type}>
                  {entry.label}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Identity count">
            <input
              type="number"
              min={1}
              max={30}
              value={identityCount}
              onChange={(event) => setIdentityCount(Number(event.target.value))}
            />
          </Field>
          <Field label="Seed (optional)" hint="Leave blank for a fresh seed each run.">
            <input value={seed} onChange={(event) => setSeed(event.target.value)} />
          </Field>
          <Button
            variant="primary"
            disabled={!runSimulation}
            pending={create.pending}
            onClick={() => void create.run()}
          >
            Run
          </Button>
        </Row>
        <ErrorNote>{create.error}</ErrorNote>
        {scenarios.length > 0 && (
          <p className="field__hint">
            {scenarios.find((entry) => entry.scenario_type === scenarioType)?.summary}
          </p>
        )}
      </Card>

      <Card title="Past runs" actions={<Button onClick={runs.reload}>Refresh</Button>}>
        <ErrorNote>{runs.error ?? openRun.error}</ErrorNote>
        {runs.loading && <Loading />}
        {!runs.loading && rows.length === 0 && <Empty>No simulation runs yet.</Empty>}
        {rows.length > 0 && (
          <Table
            head={
              <tr>
                <th>Scenario</th>
                <th>Seed</th>
                <th>Status</th>
                <th>Created</th>
                <th />
              </tr>
            }
          >
            {rows.map((run) => (
              <tr key={run.id}>
                <td>{run.scenario_type}</td>
                <td>{run.seed}</td>
                <td>
                  <Badge>{run.status}</Badge>
                </td>
                <td>
                  <Timestamp value={run.created_at} />
                </td>
                <td>
                  <Button variant="ghost" onClick={() => void openRun.run(run.id)}>
                    View
                  </Button>
                </td>
              </tr>
            ))}
          </Table>
        )}
      </Card>

      {selectedRun && (
        <RunResult run={selectedRun} onRecompute={() => void openRun.run(selectedRun.id)} />
      )}
    </>
  );
}
