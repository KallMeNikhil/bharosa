import { request } from "./client";
import type {
  ActorView,
  BatchView,
  ChannelAuthorizationView,
  CurrentCustodianView,
  CustodyGraphView,
  DigitalLinkView,
  DivergenceView,
  EvidenceView,
  IdentityEventView,
  IdentityView,
  IncidentDetailView,
  IncidentStatus,
  IncidentView,
  IssuedKeyView,
  KeyView,
  LifecycleState,
  ManufacturerView,
  ParticipantRole,
  ParticipantView,
  ProductView,
  RiskAssessmentView,
  SupplyChainEventType,
  SupplyChainEventView,
  TerritoryView,
  VerificationChannel,
  VerificationEventView,
  VerifyResponse,
} from "./types";

export const system = {
  health: () => request<{ status: string }>("/health", { anonymous: true }),
  ready: () => request<{ status: string }>("/ready", { anonymous: true }),
};

export interface VerifyRequestBody {
  serial?: string;
  digital_link?: string;
  longitude?: number;
  latitude?: number;
  reported_accuracy_m?: number;
  channel?: VerificationChannel;
}

export const publicSurface = {
  verify: (body: VerifyRequestBody) =>
    request<VerifyResponse>("/verify", { method: "POST", body, anonymous: true }),
};

export const identity = {
  me: () => request<ActorView>("/me"),

  createManufacturer: (name: string) =>
    request<ManufacturerView>("/manufacturers", {
      method: "POST",
      body: { name },
      anonymous: true,
    }),

  listKeys: () => request<KeyView[]>("/keys"),
  createKey: (keyVersion: number) =>
    request<IssuedKeyView>("/keys", { method: "POST", body: { key_version: keyVersion } }),
  rotateKey: (keyId: string, reason?: string) =>
    request<IssuedKeyView>(`/keys/${keyId}/rotate`, { method: "POST", body: { reason } }),
  revokeKey: (keyId: string, reason?: string) =>
    request<KeyView>(`/keys/${keyId}/revoke`, { method: "POST", body: { reason } }),
  compromiseKey: (keyId: string, reason?: string) =>
    request<KeyView>(`/keys/${keyId}/compromise`, { method: "POST", body: { reason } }),

  listProducts: () => request<ProductView[]>("/products"),
  createProduct: (body: { product_ref: string; name: string; gtin?: string | null }) =>
    request<ProductView>("/products", { method: "POST", body }),

  listBatches: (productId?: string) =>
    request<BatchView[]>("/batches", { query: { product_id: productId } }),
  createBatch: (body: {
    product_id: string;
    batch_ref: string;
    manufacturing_date: string;
    expiry_date?: string | null;
  }) => request<BatchView>("/batches", { method: "POST", body }),

  listIdentities: (options: { batchId?: string; limit?: number } = {}) =>
    request<IdentityView[]>("/identities", {
      query: { batch_id: options.batchId, limit: options.limit },
    }),
  getIdentity: (identityId: string) => request<IdentityView>(`/identities/${identityId}`),
  reserveIdentities: (batchId: string, count: number) =>
    request<IdentityView[]>("/identities/reserve", {
      method: "POST",
      body: { batch_id: batchId, count },
    }),
  signIdentity: (identityId: string, body: { manufacturer_key_id: string; key_handle: string }) =>
    request<IdentityView>(`/identities/${identityId}/sign`, { method: "POST", body }),
  transitionIdentity: (
    identityId: string,
    newState: LifecycleState,
    eventMetadata?: string | null,
  ) =>
    request<IdentityView>(`/identities/${identityId}/transition`, {
      method: "POST",
      body: { new_state: newState, event_metadata: eventMetadata ?? null },
    }),
  identityEvents: (identityId: string) =>
    request<IdentityEventView[]>(`/identities/${identityId}/events`),
  digitalLink: (identityId: string) =>
    request<DigitalLinkView>(`/identities/${identityId}/digital-link`),
};

export const supplyChain = {
  listParticipants: () => request<ParticipantView[]>("/supply-chain/participants"),
  createParticipant: (body: { participant_ref: string; name: string; role: ParticipantRole }) =>
    request<ParticipantView>("/supply-chain/participants", { method: "POST", body }),

  listTerritories: () => request<TerritoryView[]>("/supply-chain/territories"),
  createTerritory: (body: { territory_ref: string; name: string; boundary_wkt: string }) =>
    request<TerritoryView>("/supply-chain/territories", { method: "POST", body }),

  listAuthorizations: () =>
    request<ChannelAuthorizationView[]>("/supply-chain/channel-authorizations"),
  createAuthorization: (body: {
    participant_id: string;
    territory_id: string;
    valid_from?: string | null;
    valid_until?: string | null;
  }) =>
    request<ChannelAuthorizationView>("/supply-chain/channel-authorizations", {
      method: "POST",
      body,
    }),
  revokeAuthorization: (authorizationId: string) =>
    request<ChannelAuthorizationView>(
      `/supply-chain/channel-authorizations/${authorizationId}/revoke`,
      { method: "POST" },
    ),

  recordEvent: (body: {
    identity_id: string;
    event_type: SupplyChainEventType;
    occurred_at: string;
    source_participant_id?: string | null;
    destination_participant_id?: string | null;
    related_event_id?: string | null;
    related_identity_id?: string | null;
    reason?: string | null;
  }) => request<SupplyChainEventView>("/supply-chain/events", { method: "POST", body }),

  identityEvents: (identityId: string) =>
    request<SupplyChainEventView[]>(`/supply-chain/identities/${identityId}/events`),
  custodian: (identityId: string) =>
    request<CurrentCustodianView>(`/supply-chain/identities/${identityId}/custodian`),
};

export const intelligence = {
  verificationEvents: (identityId: string) =>
    request<VerificationEventView[]>(`/identities/${identityId}/verification-events`),

  runDetection: (identityId: string) =>
    request<EvidenceView[]>(`/identities/${identityId}/detection-runs`, { method: "POST" }),
  listEvidence: (identityId: string) => request<EvidenceView[]>(`/identities/${identityId}/evidence`),

  assessRisk: (identityId: string) =>
    request<RiskAssessmentView>(`/identities/${identityId}/risk-assessments`, { method: "POST" }),
  listAssessments: (identityId: string) =>
    request<RiskAssessmentView[]>(`/identities/${identityId}/risk-assessments`),

  listInvestigations: (identityId?: string) =>
    request<IncidentView[]>("/investigations", { query: { identity_id: identityId } }),
  openInvestigation: (body: {
    risk_assessment_id: string;
    evidence_ids: string[];
    summary: string;
  }) => request<IncidentView>("/investigations", { method: "POST", body }),
  getInvestigation: (incidentId: string) =>
    request<IncidentDetailView>(`/investigations/${incidentId}`),
  transitionInvestigation: (incidentId: string, newStatus: IncidentStatus, note?: string | null) =>
    request<IncidentView>(`/investigations/${incidentId}/transitions`, {
      method: "POST",
      body: { new_status: newStatus, note: note ?? null },
    }),
  divergence: (incidentId: string) =>
    request<DivergenceView>(`/investigations/${incidentId}/divergence`),

  custodyGraph: (identityIds: string[]) =>
    request<CustodyGraphView>("/custody-graph", { query: { identity_ids: identityIds } }),
};
