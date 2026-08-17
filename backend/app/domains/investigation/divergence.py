from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass

import networkx as nx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.supply_chain import SupplyChainEvent, SupplyChainEventType

"""Supply-chain divergence analysis.

The graph is built from Postgres rows every time it is needed and thrown away
again. Nothing here is persisted: a stored graph would become a second source
of truth about custody, and the event log is the only one.
"""

MANUFACTURER_NODE = "MANUFACTURER"

FORWARD_CUSTODY_TYPES = frozenset(
    {
        SupplyChainEventType.DISPATCH,
        SupplyChainEventType.RECEIPT,
        SupplyChainEventType.TRANSFER,
        SupplyChainEventType.REALLOCATION,
        SupplyChainEventType.RETURN,
    }
)


@dataclass(frozen=True)
class CustodyStep:
    event_id: uuid.UUID
    source: str
    destination: str
    event_type: SupplyChainEventType


@dataclass(frozen=True)
class Divergence:
    event_id: uuid.UUID
    expected_custodian: str
    observed_custodian: str
    event_type: SupplyChainEventType

    @property
    def description(self) -> str:
        return (
            f"Custody was last observed with {self.expected_custodian}, but the "
            f"next {self.event_type.value} event was recorded as leaving "
            f"{self.observed_custodian}."
        )


def _events(db: Session, identity_id: uuid.UUID) -> list[SupplyChainEvent]:
    return list(
        db.execute(
            select(SupplyChainEvent)
            .where(SupplyChainEvent.identity_id == identity_id)
            .order_by(SupplyChainEvent.sequence)
        )
        .scalars()
        .all()
    )


def custody_steps(db: Session, *, identity_id: uuid.UUID) -> list[CustodyStep]:
    steps: list[CustodyStep] = []
    for event in _events(db, identity_id):
        if event.event_type not in FORWARD_CUSTODY_TYPES:
            continue
        if event.destination_participant_id is None:
            continue
        source = (
            str(event.source_participant_id)
            if event.source_participant_id
            else MANUFACTURER_NODE
        )
        steps.append(
            CustodyStep(
                event_id=event.id,
                source=source,
                destination=str(event.destination_participant_id),
                event_type=event.event_type,
            )
        )
    return steps


def custody_path(db: Session, *, identity_id: uuid.UUID) -> list[str]:
    steps = custody_steps(db, identity_id=identity_id)
    if not steps:
        return []

    path = [steps[0].source]
    for step in steps:
        if path[-1] != step.source:
            path.append(step.source)
        path.append(step.destination)
    return path


def first_divergence(db: Session, *, identity_id: uuid.UUID) -> Divergence | None:
    custodian: str | None = None
    for step in custody_steps(db, identity_id=identity_id):
        if custodian is not None and step.source != custodian:
            return Divergence(
                event_id=step.event_id,
                expected_custodian=custodian,
                observed_custodian=step.source,
                event_type=step.event_type,
            )
        custodian = step.destination
    return None


def build_custody_graph(
    db: Session, *, identity_ids: Sequence[uuid.UUID]
) -> nx.DiGraph:
    graph = nx.DiGraph()
    for identity_id in identity_ids:
        for step in custody_steps(db, identity_id=identity_id):
            if graph.has_edge(step.source, step.destination):
                graph[step.source][step.destination]["identity_count"] += 1
            else:
                graph.add_edge(step.source, step.destination, identity_count=1)
    return graph


def common_divergence_point(
    db: Session, *, identity_ids: Sequence[uuid.UUID]
) -> str | None:
    """The most specific custody node every flagged identity passed through.

    Investigators want the deepest shared point, not the shallowest: knowing
    that a set of suspect packs all came from the manufacturer says nothing,
    while knowing they all passed through one distributor says a great deal.
    """
    paths = [custody_path(db, identity_id=identity_id) for identity_id in identity_ids]
    paths = [path for path in paths if path]
    if not paths:
        return None

    shared = set(paths[0])
    for path in paths[1:]:
        shared &= set(path)
    if not shared:
        return None

    reference = paths[0]
    return max(shared, key=reference.index)
