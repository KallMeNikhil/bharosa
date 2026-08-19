export const CAPABILITIES = [
  "CREATE_PRODUCTION_ORDER",
  "AUTHORIZE_SIGNING",
  "AUTHORIZE_PRINT",
  "MANAGE_KEYS",
  "MANAGE_SUPPLY_CHAIN_REFERENCE_DATA",
  "RECORD_SUPPLY_CHAIN_EVENT",
  "RUN_DETECTION",
  "REVIEW_RISK",
  "MANAGE_INVESTIGATION",
] as const;

export type Capability = (typeof CAPABILITIES)[number];

export const LIFECYCLE_STATES = [
  "RESERVED",
  "SIGNED",
  "PRINTED",
  "PRINT_VERIFIED",
  "RECONCILED",
  "ACTIVATED",
  "PRINT_REJECTED",
] as const;

export type LifecycleState = (typeof LIFECYCLE_STATES)[number];

export const LIFECYCLE_PATH: LifecycleState[] = [
  "RESERVED",
  "SIGNED",
  "PRINTED",
  "PRINT_VERIFIED",
  "RECONCILED",
  "ACTIVATED",
];

export const LEGAL_TRANSITIONS: Record<LifecycleState, LifecycleState[]> = {
  RESERVED: ["SIGNED"],
  SIGNED: ["PRINTED"],
  PRINTED: ["PRINT_VERIFIED", "PRINT_REJECTED"],
  PRINT_VERIFIED: ["RECONCILED", "PRINT_REJECTED"],
  RECONCILED: ["ACTIVATED", "PRINT_REJECTED"],
  ACTIVATED: [],
  PRINT_REJECTED: [],
};

export const CAPABILITY_FOR_TRANSITION: Partial<Record<LifecycleState, Capability>> = {
  PRINTED: "AUTHORIZE_PRINT",
  PRINT_VERIFIED: "AUTHORIZE_PRINT",
  PRINT_REJECTED: "AUTHORIZE_PRINT",
  RECONCILED: "AUTHORIZE_PRINT",
  ACTIVATED: "CREATE_PRODUCTION_ORDER",
};

export type KeyStatus = "ACTIVE" | "ROTATED" | "REVOKED" | "COMPROMISED";
export type ProductStatus = "ACTIVE" | "RETIRED";
export type BatchStatus = "OPEN" | "CLOSED";

export const PARTICIPANT_ROLES = ["DEPOT", "DISTRIBUTOR", "RETAILER"] as const;
export type ParticipantRole = (typeof PARTICIPANT_ROLES)[number];

export const SUPPLY_CHAIN_EVENT_TYPES = [
  "DISPATCH",
  "RECEIPT",
  "TRANSFER",
  "RETURN",
  "REALLOCATION",
  "RETAIL_PLACEMENT",
  "CUSTODY_ADJUSTMENT",
] as const;
export type SupplyChainEventType = (typeof SUPPLY_CHAIN_EVENT_TYPES)[number];

export const VERIFICATION_STATES = [
  "GENUINE",
  "CAUTION",
  "INVALID",
  "ALREADY_REPORTED",
  "UNAVAILABLE",
] as const;
export type VerificationState = (typeof VERIFICATION_STATES)[number];

export const VERIFICATION_CHANNELS = [
  "WEB",
  "API",
  "RETAILER_APP",
  "FIELD_INVESTIGATOR",
] as const;
export type VerificationChannel = (typeof VERIFICATION_CHANNELS)[number];

export type FraudFamily = "FULL_COUNTERFEIT" | "CODE_CLONING" | "REFILLING" | "DIVERSION";

export type SignalType =
  | "SIGNATURE_INVALID"
  | "UNTRUSTED_KEY_AT_SCAN"
  | "PRE_ACTIVATION_SCAN"
  | "IMPOSSIBLE_TRAVEL"
  | "GEOGRAPHIC_SPREAD"
  | "SCAN_VELOCITY"
  | "POST_SALE_SCAN_RESURGENCE"
  | "DORMANCY_REACTIVATION"
  | "TERRITORY_VIOLATION"
  | "CHANNEL_VIOLATION";

export type ConfidenceLevel = "NEGLIGIBLE" | "LOW" | "MODERATE" | "HIGH";

export const INCIDENT_STATUSES = [
  "OPEN",
  "UNDER_REVIEW",
  "SUBSTANTIATED",
  "DISMISSED",
] as const;
export type IncidentStatus = (typeof INCIDENT_STATUSES)[number];

export const LEGAL_INCIDENT_TRANSITIONS: Record<IncidentStatus, IncidentStatus[]> = {
  OPEN: ["UNDER_REVIEW", "DISMISSED"],
  UNDER_REVIEW: ["SUBSTANTIATED", "DISMISSED"],
  SUBSTANTIATED: [],
  DISMISSED: [],
};

export interface ActorView {
  actor_id: string;
  manufacturer_id: string;
  capabilities: Capability[];
}

export interface ManufacturerView {
  id: string;
  name: string;
  status: string;
  created_at: string;
}

export interface KeyView {
  id: string;
  manufacturer_id: string;
  key_version: number;
  status: KeyStatus;
  valid_from: string;
  valid_to: string | null;
}

export interface IssuedKeyView {
  key: KeyView;
  key_handle: string;
}

export interface ProductView {
  id: string;
  manufacturer_id: string;
  product_ref: string;
  name: string;
  gtin: string | null;
  status: ProductStatus;
}

export interface BatchView {
  id: string;
  manufacturer_id: string;
  product_id: string;
  batch_ref: string;
  manufacturing_date: string | null;
  expiry_date: string | null;
  status: BatchStatus;
}

export interface IdentityView {
  id: string;
  manufacturer_id: string;
  batch_id: string;
  serial: string;
  lifecycle_state: LifecycleState;
  manufacturer_key_id: string | null;
  created_at: string;
  signed_at: string | null;
  activated_at: string | null;
}

export interface IdentityEventView {
  sequence: number;
  event_type: string;
  previous_state: LifecycleState | null;
  new_state: LifecycleState;
  actor: string | null;
  occurred_at: string;
}

export interface DigitalLinkView {
  identity_id: string;
  uri: string;
}

export interface ParticipantView {
  id: string;
  manufacturer_id: string;
  participant_ref: string;
  name: string;
  role: ParticipantRole;
}

export interface TerritoryView {
  id: string;
  manufacturer_id: string;
  territory_ref: string;
  name: string;
}

export interface ChannelAuthorizationView {
  id: string;
  manufacturer_id: string;
  participant_id: string;
  territory_id: string;
  valid_from: string;
  valid_until: string | null;
}

export interface SupplyChainEventView {
  id: string;
  identity_id: string;
  sequence: number;
  event_type: SupplyChainEventType;
  source_participant_id: string | null;
  destination_participant_id: string | null;
  related_event_id: string | null;
  related_identity_id: string | null;
  reason: string | null;
  occurred_at: string;
}

export interface CurrentCustodianView {
  identity_id: string;
  custodian_id: string | null;
}

export interface VerificationEventView {
  id: string;
  sequence: number;
  state: VerificationState;
  channel: VerificationChannel;
  signature_valid: boolean;
  lifecycle_state_at_scan: LifecycleState;
  key_status_at_scan: KeyStatus | null;
  coarse_cell: string | null;
  occurred_at: string;
}

export interface EvidenceView {
  id: string;
  identity_id: string;
  sequence: number;
  detector_id: string;
  detector_version: number;
  signal_type: SignalType;
  fraud_family: FraudFamily;
  log_likelihood_ratio: number;
  explanation: string;
  window_start: string;
  window_end: string;
  generated_at: string;
}

export interface ContributionView {
  evidence_id: string;
  weight: number;
  contributed_log_odds: number;
  benign_explanation: string;
}

export interface RiskAssessmentView {
  id: string;
  identity_id: string;
  sequence: number;
  ruleset_version: number;
  prior_log_odds: number;
  posterior_log_odds: number;
  confidence: ConfidenceLevel;
  window_start: string;
  window_end: string;
  generated_at: string;
  contributions: ContributionView[];
}

export interface IncidentEventView {
  sequence: number;
  previous_status: IncidentStatus | null;
  new_status: IncidentStatus;
  note: string | null;
  actor: string;
  occurred_at: string;
}

export interface IncidentView {
  id: string;
  identity_id: string;
  risk_assessment_id: string;
  status: IncidentStatus;
  summary: string;
  opened_by: string;
  opened_at: string;
  resolved_at: string | null;
}

export interface IncidentDetailView extends IncidentView {
  cited_evidence: EvidenceView[];
  events: IncidentEventView[];
}

export interface DivergenceView {
  identity_id: string;
  event_id: string | null;
  expected_custodian: string | null;
  observed_custodian: string | null;
  description: string | null;
}

export interface CustodyEdgeView {
  source: string;
  destination: string;
  identity_count: number;
}

export interface CustodyGraphView {
  edges: CustodyEdgeView[];
  common_divergence_point: string | null;
}

export interface VerifyResponse {
  state: VerificationState;
  message: string;
  checked_at: string;
}
