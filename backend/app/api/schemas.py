from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.authorization import Capability
from app.domains.detection import FraudFamily, SignalType
from app.domains.identity import BatchStatus, KeyStatus, LifecycleState, ProductStatus
from app.domains.investigation import IncidentStatus
from app.domains.risk import ConfidenceLevel
from app.domains.simulation import GroundTruthClassification, ScenarioType, SimulationRunStatus
from app.domains.supply_chain import ParticipantRole, SupplyChainEventType


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ActorView(BaseModel):
    actor_id: str
    manufacturer_id: uuid.UUID
    capabilities: list[Capability]


class ManufacturerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class ManufacturerView(ORMModel):
    id: uuid.UUID
    name: str
    status: str
    created_at: datetime


class KeyCreate(BaseModel):
    key_version: int = Field(ge=1, le=2**31 - 1)


class KeyView(ORMModel):
    id: uuid.UUID
    manufacturer_id: uuid.UUID
    key_version: int
    status: KeyStatus
    valid_from: datetime
    valid_to: datetime | None


class IssuedKeyView(BaseModel):
    key: KeyView
    key_handle: str


class KeyStatusChange(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class ProductCreate(BaseModel):
    product_ref: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    gtin: str | None = Field(default=None, min_length=14, max_length=14)


class ProductView(ORMModel):
    id: uuid.UUID
    manufacturer_id: uuid.UUID
    product_ref: str
    name: str
    gtin: str | None
    status: ProductStatus


class BatchCreate(BaseModel):
    product_id: uuid.UUID
    batch_ref: str = Field(min_length=1, max_length=64)
    manufacturing_date: date
    expiry_date: date | None = None


class BatchView(ORMModel):
    id: uuid.UUID
    manufacturer_id: uuid.UUID
    product_id: uuid.UUID
    batch_ref: str
    manufacturing_date: date | None
    expiry_date: date | None
    status: BatchStatus


class IdentityReserve(BaseModel):
    batch_id: uuid.UUID
    count: int = Field(default=1, ge=1, le=1000)


class IdentitySign(BaseModel):
    manufacturer_key_id: uuid.UUID
    key_handle: str


class IdentityTransition(BaseModel):
    new_state: LifecycleState
    event_metadata: str | None = Field(default=None, max_length=2000)


class IdentityView(ORMModel):
    id: uuid.UUID
    manufacturer_id: uuid.UUID
    batch_id: uuid.UUID
    serial: str
    lifecycle_state: LifecycleState
    manufacturer_key_id: uuid.UUID | None
    created_at: datetime
    signed_at: datetime | None
    activated_at: datetime | None


class DigitalLinkView(BaseModel):
    identity_id: uuid.UUID
    uri: str


class IdentityEventView(ORMModel):
    sequence: int
    event_type: str
    previous_state: LifecycleState | None
    new_state: LifecycleState
    actor: str | None
    occurred_at: datetime


class ParticipantCreate(BaseModel):
    participant_ref: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    role: ParticipantRole


class ParticipantView(ORMModel):
    id: uuid.UUID
    manufacturer_id: uuid.UUID
    participant_ref: str
    name: str
    role: ParticipantRole


class TerritoryCreate(BaseModel):
    territory_ref: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    boundary_wkt: str = Field(min_length=1)


class TerritoryView(ORMModel):
    id: uuid.UUID
    manufacturer_id: uuid.UUID
    territory_ref: str
    name: str


class ChannelAuthorizationCreate(BaseModel):
    participant_id: uuid.UUID
    territory_id: uuid.UUID
    valid_from: datetime | None = None
    valid_until: datetime | None = None


class ChannelAuthorizationView(ORMModel):
    id: uuid.UUID
    manufacturer_id: uuid.UUID
    participant_id: uuid.UUID
    territory_id: uuid.UUID
    valid_from: datetime
    valid_until: datetime | None


class SupplyChainEventCreate(BaseModel):
    identity_id: uuid.UUID
    event_type: SupplyChainEventType
    occurred_at: datetime
    source_participant_id: uuid.UUID | None = None
    destination_participant_id: uuid.UUID | None = None
    related_event_id: uuid.UUID | None = None
    related_identity_id: uuid.UUID | None = None
    reason: str | None = Field(default=None, max_length=500)


class SupplyChainEventView(ORMModel):
    id: uuid.UUID
    identity_id: uuid.UUID
    sequence: int
    event_type: SupplyChainEventType
    source_participant_id: uuid.UUID | None
    destination_participant_id: uuid.UUID | None
    related_event_id: uuid.UUID | None
    related_identity_id: uuid.UUID | None
    reason: str | None
    occurred_at: datetime


class CurrentCustodianView(BaseModel):
    identity_id: uuid.UUID
    custodian_id: uuid.UUID | None


class VerificationEventView(ORMModel):
    id: uuid.UUID
    sequence: int
    state: str
    channel: str
    signature_valid: bool
    lifecycle_state_at_scan: str
    key_status_at_scan: str | None
    coarse_cell: str | None
    occurred_at: datetime


class EvidenceView(ORMModel):
    id: uuid.UUID
    identity_id: uuid.UUID
    sequence: int
    detector_id: str
    detector_version: int
    signal_type: SignalType
    fraud_family: FraudFamily
    log_likelihood_ratio: float
    explanation: str
    window_start: datetime
    window_end: datetime
    generated_at: datetime


class ContributionView(ORMModel):
    evidence_id: uuid.UUID
    weight: float
    contributed_log_odds: float
    benign_explanation: str


class RiskAssessmentView(ORMModel):
    id: uuid.UUID
    identity_id: uuid.UUID
    sequence: int
    ruleset_version: int
    prior_log_odds: float
    posterior_log_odds: float
    confidence: ConfidenceLevel
    window_start: datetime
    window_end: datetime
    generated_at: datetime
    contributions: list[ContributionView]


class IncidentOpen(BaseModel):
    risk_assessment_id: uuid.UUID
    evidence_ids: list[uuid.UUID] = Field(min_length=1)
    summary: str = Field(min_length=1, max_length=1000)


class IncidentTransition(BaseModel):
    new_status: IncidentStatus
    note: str | None = Field(default=None, max_length=2000)


class IncidentEventView(ORMModel):
    sequence: int
    previous_status: IncidentStatus | None
    new_status: IncidentStatus
    note: str | None
    actor: str
    occurred_at: datetime


class IncidentView(ORMModel):
    id: uuid.UUID
    identity_id: uuid.UUID
    risk_assessment_id: uuid.UUID
    status: IncidentStatus
    summary: str
    opened_by: str
    opened_at: datetime
    resolved_at: datetime | None


class IncidentDetailView(IncidentView):
    cited_evidence: list[EvidenceView]
    events: list[IncidentEventView]


class CustodyEdgeView(BaseModel):
    source: str
    destination: str
    identity_count: int


class DivergenceView(BaseModel):
    identity_id: uuid.UUID
    event_id: uuid.UUID | None
    expected_custodian: str | None
    observed_custodian: str | None
    description: str | None


class CustodyGraphView(BaseModel):
    edges: list[CustodyEdgeView]
    common_divergence_point: str | None


class ScenarioCatalogueEntryView(BaseModel):
    scenario_type: ScenarioType
    label: str
    summary: str
    injects_fraud: bool


class SimulationRunCreate(BaseModel):
    scenario_type: ScenarioType
    seed: int | None = Field(default=None)
    identity_count: int = Field(default=6, ge=1, le=30)


class SimulationRunView(ORMModel):
    id: uuid.UUID
    manufacturer_id: uuid.UUID
    scenario_type: ScenarioType
    seed: int
    identity_count: int
    status: SimulationRunStatus
    triggered_by: str
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class GroundTruthEntryView(ORMModel):
    id: uuid.UUID
    identity_id: uuid.UUID
    sequence: int
    classification: GroundTruthClassification
    injection_type: str | None
    expected_signal_types: str
    notes: str


class SimulationEvaluationView(ORMModel):
    id: uuid.UUID
    simulation_run_id: uuid.UUID
    sequence: int
    true_positive_count: int
    false_positive_count: int
    true_negative_count: int
    false_negative_count: int
    precision: float | None
    recall: float | None
    detection_rate: float | None
    missed_fraud_rate: float | None
    investigation_true_positive_count: int
    investigation_false_positive_count: int
    per_detector_breakdown: dict
    generated_at: datetime


class SimulationRunDetailView(SimulationRunView):
    ground_truth: list[GroundTruthEntryView]
    latest_evaluation: SimulationEvaluationView | None
