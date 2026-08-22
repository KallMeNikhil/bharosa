from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.authorization import ActorContext
from app.domains.detection import identity_evidence, run_detection
from app.domains.identity import ProductIdentity
from app.domains.investigation import open_incident
from app.domains.risk import ELEVATED_CONFIDENCE_LEVELS, assess_identity
from app.domains.simulation.generator import (
    Topology,
    build_benign_unusual_population,
    build_legitimate_population,
)
from app.domains.simulation.injections import (
    GroundTruthDraft,
    inject_code_cloning,
    inject_combined,
    inject_diversion,
    inject_full_counterfeit,
    inject_refilling,
    legitimate_draft,
)
from app.domains.simulation.models import ScenarioType
from app.domains.simulation.rng import SimulationRandom
from app.domains.simulation.scenarios import INJECTION_FRACTION_DENOMINATOR

_SINGLE_INJECTORS = {
    ScenarioType.FULL_COUNTERFEIT: inject_full_counterfeit,
    ScenarioType.CODE_CLONING: inject_code_cloning,
    ScenarioType.REFILLING: inject_refilling,
    ScenarioType.DIVERSION: inject_diversion,
    ScenarioType.COMBINED_MULTI_SIGNAL: inject_combined,
}

_LEGITIMATE_NOTES = (
    "Fully legitimate identity: signed, activated, moved through a normal "
    "custody path and scanned normally."
)

_BENIGN_UNUSUAL_NOTES = (
    "Legitimate identity exercising returns, reallocation between a "
    "distributor's own retailers, and repeated same-territory scans below "
    "every detector threshold."
)


@dataclass(frozen=True)
class GeneratedIdentity:
    identity: ProductIdentity
    draft: GroundTruthDraft


def _injection_indices(scenario_type: ScenarioType, identity_count: int) -> frozenset[int]:
    if scenario_type not in _SINGLE_INJECTORS:
        return frozenset()
    count = max(1, identity_count // INJECTION_FRACTION_DENOMINATOR)
    return frozenset(range(count))


def generate_population(
    db: Session,
    *,
    topology: Topology,
    scenario_type: ScenarioType,
    rng: SimulationRandom,
    actor: ActorContext,
    identity_count: int,
    run_start: datetime,
) -> list[GeneratedIdentity]:
    generated: list[GeneratedIdentity] = []
    injected_indices = _injection_indices(scenario_type, identity_count)

    for index in range(identity_count):
        base_time = run_start + timedelta(days=index)

        if scenario_type is ScenarioType.BENIGN_ANOMALY:
            identity = build_benign_unusual_population(
                db, topology=topology, rng=rng, actor=actor, base_time=base_time
            )
            draft = legitimate_draft(_BENIGN_UNUSUAL_NOTES)
        elif index in injected_indices:
            injector = _SINGLE_INJECTORS[scenario_type]
            identity, draft = injector(
                db, topology=topology, rng=rng, actor=actor, base_time=base_time
            )
        else:
            identity = build_legitimate_population(
                db, topology=topology, rng=rng, actor=actor, base_time=base_time
            )
            draft = legitimate_draft(_LEGITIMATE_NOTES)

        generated.append(GeneratedIdentity(identity=identity, draft=draft))

    return generated


def run_pipeline(
    db: Session, *, generated: list[GeneratedIdentity], actor: ActorContext, now: datetime
) -> None:
    for entry in generated:
        run_detection(db, identity=entry.identity, actor=actor, now=now)

    for entry in generated:
        evidence = identity_evidence(db, identity_id=entry.identity.id)
        if not evidence:
            continue
        assessment = assess_identity(db, identity=entry.identity, actor=actor, now=now)
        if assessment.confidence in ELEVATED_CONFIDENCE_LEVELS:
            open_incident(
                db,
                assessment=assessment,
                evidence=evidence,
                summary=(
                    f"Simulation-generated elevated risk for identity "
                    f"{entry.identity.id}: {assessment.confidence.value}."
                ),
                actor=actor,
            )
