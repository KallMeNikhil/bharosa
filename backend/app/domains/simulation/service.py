from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.authorization import ActorContext, Capability
from app.core.event_chain import compute_event_hash, next_chain_link
from app.domains.detection import SignalType, run_detection
from app.domains.identity import (
    DevelopmentOnlySigner,
    Manufacturer,
    ManufacturerKey,
    ProductIdentity,
    Signer,
)
from app.domains.simulation.evaluation import EvaluationResult, evaluate
from app.domains.simulation.generator import build_topology, simulation_actor
from app.domains.simulation.injections import GroundTruthDraft
from app.domains.simulation.models import (
    ScenarioType,
    SimulationEvaluation,
    SimulationGroundTruthEntry,
    SimulationRun,
    SimulationRunStatus,
)
from app.domains.simulation.rng import SimulationRandom
from app.domains.simulation.runner import GeneratedIdentity, generate_population, run_pipeline
from app.domains.simulation.scenarios import (
    DEFAULT_IDENTITY_COUNT,
    MAX_IDENTITY_COUNT,
    MIN_IDENTITY_COUNT,
)


class ManufacturerNotOnboardedError(ValueError):
    def __init__(self, manufacturer_id: uuid.UUID) -> None:
        self.manufacturer_id = manufacturer_id
        super().__init__(
            f"Manufacturer {manufacturer_id} is not onboarded. A simulation "
            f"runs inside the caller's own tenant and reuses its onboarding, "
            f"exactly like every other domain; register the manufacturer "
            f"first."
        )


class InvalidIdentityCountError(ValueError):
    def __init__(self, identity_count: int) -> None:
        self.identity_count = identity_count
        super().__init__(
            f"identity_count must be between {MIN_IDENTITY_COUNT} and "
            f"{MAX_IDENTITY_COUNT}, got {identity_count}."
        )


class SimulationRunNotCompletedError(ValueError):
    def __init__(self, run_id: uuid.UUID, status: SimulationRunStatus) -> None:
        self.run_id = run_id
        self.status = status
        super().__init__(
            f"Simulation run {run_id} is {status.value}, not COMPLETED. "
            f"Evaluation requires a completed run."
        )


def _default_seed() -> int:
    return int(time.time_ns() % (2**31 - 1))


def _next_key_version(db: Session, *, manufacturer_id: uuid.UUID) -> int:
    highest = db.execute(
        select(ManufacturerKey.key_version)
        .where(ManufacturerKey.manufacturer_id == manufacturer_id)
        .order_by(ManufacturerKey.key_version.desc())
        .limit(1)
    ).scalar_one_or_none()
    return 1 if highest is None else highest + 1


def _record_ground_truth(
    db: Session, *, run: SimulationRun, generated: list[GeneratedIdentity]
) -> list[SimulationGroundTruthEntry]:
    entries: list[SimulationGroundTruthEntry] = []
    for entry in generated:
        sequence, previous_event_hash = next_chain_link(
            db,
            sequence_column=SimulationGroundTruthEntry.sequence,
            event_hash_column=SimulationGroundTruthEntry.event_hash,
            scope_clause=SimulationGroundTruthEntry.simulation_run_id == run.id,
        )
        expected_signal_types = ",".join(s.value for s in entry.draft.expected_signal_types)
        event_hash = compute_event_hash(
            previous_event_hash=previous_event_hash,
            event_kind="simulation_ground_truth_entry",
            fields=[
                str(run.manufacturer_id),
                str(run.id),
                str(sequence),
                str(entry.identity.id),
                entry.draft.classification.value,
                entry.draft.injection_type,
                expected_signal_types,
            ],
        )
        row = SimulationGroundTruthEntry(
            manufacturer_id=run.manufacturer_id,
            simulation_run_id=run.id,
            identity_id=entry.identity.id,
            sequence=sequence,
            classification=entry.draft.classification,
            injection_type=entry.draft.injection_type,
            expected_signal_types=expected_signal_types,
            notes=entry.draft.notes,
            previous_event_hash=previous_event_hash,
            event_hash=event_hash,
        )
        db.add(row)
        db.flush()
        entries.append(row)
    return entries


def _record_evaluation(
    db: Session, *, run: SimulationRun, result: EvaluationResult
) -> SimulationEvaluation:
    sequence, previous_event_hash = next_chain_link(
        db,
        sequence_column=SimulationEvaluation.sequence,
        event_hash_column=SimulationEvaluation.event_hash,
        scope_clause=SimulationEvaluation.simulation_run_id == run.id,
    )
    event_hash = compute_event_hash(
        previous_event_hash=previous_event_hash,
        event_kind="simulation_evaluation",
        fields=[
            str(run.manufacturer_id),
            str(run.id),
            str(sequence),
            str(result.true_positive_count),
            str(result.false_positive_count),
            str(result.true_negative_count),
            str(result.false_negative_count),
        ],
    )
    evaluation = SimulationEvaluation(
        manufacturer_id=run.manufacturer_id,
        simulation_run_id=run.id,
        sequence=sequence,
        true_positive_count=result.true_positive_count,
        false_positive_count=result.false_positive_count,
        true_negative_count=result.true_negative_count,
        false_negative_count=result.false_negative_count,
        precision=result.precision,
        recall=result.recall,
        detection_rate=result.detection_rate,
        missed_fraud_rate=result.missed_fraud_rate,
        investigation_true_positive_count=result.investigation_true_positive_count,
        investigation_false_positive_count=result.investigation_false_positive_count,
        per_detector_breakdown=result.per_detector_breakdown,
        previous_event_hash=previous_event_hash,
        event_hash=event_hash,
    )
    db.add(evaluation)
    db.flush()
    return evaluation


def _draft_from_entry(entry: SimulationGroundTruthEntry) -> GroundTruthDraft:
    expected = tuple(
        SignalType(value) for value in entry.expected_signal_types.split(",") if value
    )
    return GroundTruthDraft(
        classification=entry.classification,
        injection_type=entry.injection_type,
        expected_signal_types=expected,
        notes=entry.notes,
    )


def run_simulation(
    db: Session,
    *,
    scenario_type: ScenarioType,
    actor: ActorContext,
    seed: int | None = None,
    identity_count: int = DEFAULT_IDENTITY_COUNT,
    signer: Signer | None = None,
    now: datetime | None = None,
) -> tuple[SimulationRun, list[SimulationGroundTruthEntry], SimulationEvaluation]:
    actor.require(Capability.RUN_SIMULATION)

    if not (MIN_IDENTITY_COUNT <= identity_count <= MAX_IDENTITY_COUNT):
        raise InvalidIdentityCountError(identity_count)

    manufacturer = db.get(Manufacturer, actor.manufacturer_id)
    if manufacturer is None:
        raise ManufacturerNotOnboardedError(actor.manufacturer_id)

    resolved_seed = _default_seed() if seed is None else seed
    run_start = (now or datetime.now(UTC)).astimezone(UTC)
    run_ref = uuid.uuid4().hex[:10]

    run = SimulationRun(
        manufacturer_id=manufacturer.id,
        run_ref=run_ref,
        scenario_type=scenario_type,
        seed=resolved_seed,
        identity_count=identity_count,
        status=SimulationRunStatus.RUNNING,
        triggered_by=actor.actor_id,
        started_at=run_start,
    )
    db.add(run)
    db.flush()

    try:
        rng = SimulationRandom(resolved_seed)
        internal_actor = simulation_actor(manufacturer.id)
        topology = build_topology(
            db,
            manufacturer=manufacturer,
            signer=signer or DevelopmentOnlySigner(),
            run_ref=run_ref,
            key_version=_next_key_version(db, manufacturer_id=manufacturer.id),
            actor=internal_actor,
            now=run_start,
        )
        generated = generate_population(
            db,
            topology=topology,
            scenario_type=scenario_type,
            rng=rng,
            actor=internal_actor,
            identity_count=identity_count,
            run_start=run_start,
        )
        pipeline_now = run_start + timedelta(days=identity_count + 14)
        run_pipeline(db, generated=generated, actor=internal_actor, now=pipeline_now)

        ground_truth_entries = _record_ground_truth(db, run=run, generated=generated)
        result = evaluate(db, generated=generated)
        evaluation = _record_evaluation(db, run=run, result=result)

        run.status = SimulationRunStatus.COMPLETED
        run.completed_at = datetime.now(UTC)
        db.flush()
    except Exception as exc:
        run.status = SimulationRunStatus.FAILED
        run.error_message = str(exc)[:2000]
        run.completed_at = datetime.now(UTC)
        db.flush()
        raise

    return run, ground_truth_entries, evaluation


def get_run(db: Session, *, run_id: uuid.UUID) -> SimulationRun | None:
    return db.get(SimulationRun, run_id)


def list_runs(db: Session) -> list[SimulationRun]:
    return list(
        db.execute(select(SimulationRun).order_by(SimulationRun.created_at.desc()))
        .scalars()
        .all()
    )


def ground_truth_for_run(
    db: Session, *, run_id: uuid.UUID
) -> list[SimulationGroundTruthEntry]:
    return list(
        db.execute(
            select(SimulationGroundTruthEntry)
            .where(SimulationGroundTruthEntry.simulation_run_id == run_id)
            .order_by(SimulationGroundTruthEntry.sequence)
        )
        .scalars()
        .all()
    )


def latest_evaluation(db: Session, *, run_id: uuid.UUID) -> SimulationEvaluation | None:
    return db.execute(
        select(SimulationEvaluation)
        .where(SimulationEvaluation.simulation_run_id == run_id)
        .order_by(SimulationEvaluation.sequence.desc())
        .limit(1)
    ).scalar_one_or_none()


def evaluation_history(db: Session, *, run_id: uuid.UUID) -> list[SimulationEvaluation]:
    return list(
        db.execute(
            select(SimulationEvaluation)
            .where(SimulationEvaluation.simulation_run_id == run_id)
            .order_by(SimulationEvaluation.sequence)
        )
        .scalars()
        .all()
    )


def recompute_evaluation(
    db: Session, *, run: SimulationRun, actor: ActorContext, now: datetime | None = None
) -> SimulationEvaluation:
    actor.require(Capability.RUN_SIMULATION)

    if run.status is not SimulationRunStatus.COMPLETED:
        raise SimulationRunNotCompletedError(run.id, run.status)

    ground_truth_entries = ground_truth_for_run(db, run_id=run.id)
    identities_by_id = {
        row.id: row
        for row in db.execute(
            select(ProductIdentity).where(
                ProductIdentity.id.in_([entry.identity_id for entry in ground_truth_entries])
            )
        )
        .scalars()
        .all()
    }

    generated = [
        GeneratedIdentity(
            identity=identities_by_id[entry.identity_id],
            draft=_draft_from_entry(entry),
        )
        for entry in ground_truth_entries
    ]

    internal_actor = simulation_actor(run.manufacturer_id)
    pipeline_now = now or datetime.now(UTC)
    for entry in generated:
        run_detection(db, identity=entry.identity, actor=internal_actor, now=pipeline_now)

    result = evaluate(db, generated=generated)
    return _record_evaluation(db, run=run, result=result)
