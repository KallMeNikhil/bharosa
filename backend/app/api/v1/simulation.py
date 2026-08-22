from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api import schemas
from app.api.deps import current_actor, owned_or_404, requires, tenant_db
from app.core.authorization import ActorContext, Capability
from app.domains.simulation import (
    SCENARIO_CATALOGUE,
    InvalidIdentityCountError,
    ManufacturerNotOnboardedError,
    SimulationRun,
    SimulationRunNotCompletedError,
    get_run,
    ground_truth_for_run,
    latest_evaluation,
    list_runs,
    recompute_evaluation,
    run_simulation,
)

router = APIRouter(tags=["simulation"])


def _run(db: Session, actor: ActorContext, run_id: uuid.UUID) -> SimulationRun:
    return owned_or_404(get_run(db, run_id=run_id), actor.manufacturer_id, name="Simulation run")


def _detail_view(db: Session, run: SimulationRun) -> schemas.SimulationRunDetailView:
    ground_truth = ground_truth_for_run(db, run_id=run.id)
    evaluation = latest_evaluation(db, run_id=run.id)
    return schemas.SimulationRunDetailView(
        **schemas.SimulationRunView.model_validate(run).model_dump(),
        ground_truth=[
            schemas.GroundTruthEntryView.model_validate(entry) for entry in ground_truth
        ],
        latest_evaluation=(
            schemas.SimulationEvaluationView.model_validate(evaluation)
            if evaluation is not None
            else None
        ),
    )


@router.get(
    "/simulations/catalogue",
    response_model=list[schemas.ScenarioCatalogueEntryView],
)
def scenario_catalogue() -> list[schemas.ScenarioCatalogueEntryView]:
    return [
        schemas.ScenarioCatalogueEntryView(
            scenario_type=description.scenario_type,
            label=description.label,
            summary=description.summary,
            injects_fraud=description.injects_fraud,
        )
        for description in SCENARIO_CATALOGUE.values()
    ]


@router.post(
    "/simulations",
    response_model=schemas.SimulationRunDetailView,
    status_code=status.HTTP_201_CREATED,
)
def create_simulation(
    body: schemas.SimulationRunCreate,
    actor: ActorContext = Depends(requires(Capability.RUN_SIMULATION)),
    db: Session = Depends(tenant_db),
) -> schemas.SimulationRunDetailView:
    try:
        run, _, _ = run_simulation(
            db,
            scenario_type=body.scenario_type,
            actor=actor,
            seed=body.seed,
            identity_count=body.identity_count,
        )
    except (InvalidIdentityCountError, ManufacturerNotOnboardedError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    db.commit()
    return _detail_view(db, run)


@router.get("/simulations", response_model=list[schemas.SimulationRunView])
def list_simulations(db: Session = Depends(tenant_db)) -> list[SimulationRun]:
    return list_runs(db)


@router.get("/simulations/{run_id}", response_model=schemas.SimulationRunDetailView)
def get_simulation(
    run_id: uuid.UUID,
    actor: ActorContext = Depends(current_actor),
    db: Session = Depends(tenant_db),
) -> schemas.SimulationRunDetailView:
    run = _run(db, actor, run_id)
    return _detail_view(db, run)


@router.get(
    "/simulations/{run_id}/ground-truth",
    response_model=list[schemas.GroundTruthEntryView],
)
def get_simulation_ground_truth(
    run_id: uuid.UUID,
    actor: ActorContext = Depends(current_actor),
    db: Session = Depends(tenant_db),
):
    run = _run(db, actor, run_id)
    return ground_truth_for_run(db, run_id=run.id)


@router.get(
    "/simulations/{run_id}/evaluation",
    response_model=schemas.SimulationEvaluationView,
)
def get_simulation_evaluation(
    run_id: uuid.UUID,
    actor: ActorContext = Depends(current_actor),
    db: Session = Depends(tenant_db),
):
    run = _run(db, actor, run_id)
    evaluation = latest_evaluation(db, run_id=run.id)
    if evaluation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This simulation run has no evaluation yet.",
        )
    return evaluation


@router.post(
    "/simulations/{run_id}/evaluation",
    response_model=schemas.SimulationEvaluationView,
    status_code=status.HTTP_201_CREATED,
)
def recompute_simulation_evaluation(
    run_id: uuid.UUID,
    actor: ActorContext = Depends(requires(Capability.RUN_SIMULATION)),
    db: Session = Depends(tenant_db),
):
    run = _run(db, actor, run_id)
    try:
        evaluation = recompute_evaluation(db, run=run, actor=actor)
    except SimulationRunNotCompletedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    db.commit()
    return evaluation
