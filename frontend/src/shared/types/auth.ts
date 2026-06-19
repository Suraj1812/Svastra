export type Role = "provider" | "patient" | "caregiver";
export type FlowMode = Role | "login";
export type FlowStep = "mobile" | "otp" | "registration" | "consent" | "dashboard";

export type ApiEnvelope<T> = {
  success: boolean;
  data: T | null;
  message: string | null;
  error: {
    code: string;
    message: string;
    details?: unknown;
    request_id?: string;
  } | null;
};

export type UserSummary = {
  id: number;
  role: Role;
  full_name: string;
  mobile_number: string;
  professional_category?: ReferenceTerm | null;
  gender?: ReferenceTerm | null;
  preferred_language?: ReferenceTerm | null;
  relationship_to_patient?: ReferenceTerm | null;
};

export type SessionSummary = {
  session_token: string;
  expires_at: string;
  is_active: boolean;
};

export type ConsentSummary = {
  patient_id: number;
  consent_version: string;
  accepted_at: string;
  application_name: string;
  app_version: string;
  ip_address?: string | null;
};

export type AuthResult = {
  user: UserSummary;
  session: SessionSummary;
  dashboard_route: string;
  consent?: ConsentSummary;
};

export type ConsentDocument = {
  consent_version: string;
  document: string;
};

export type ValidateSessionResult = AuthResult & {
  valid: boolean;
};

export type PermissionSummary = {
  code: string;
  label: string;
};

export type PermissionsResult = {
  user_id: number;
  role: Role;
  permissions: PermissionSummary[];
};

export type ConsentStatusResult = {
  patient_id: number;
  current_consent_version: string;
  consent_version: string;
  accepted: boolean;
  accepted_at: string | null;
  consent_status: string;
  application_name?: string | null;
  app_version?: string | null;
};

export type ConsentType = "provider_access" | "caregiver_access";
export type ConsentState = "PENDING" | "ACTIVE" | "REJECTED" | "REVOKED" | "EXPIRED";

export type RelationshipConsentSummary = {
  id: number;
  alias: string;
  registered_full_name: string;
  requestor_name: string;
  requestor_role: string;
  role: string;
  consent_type: ConsentType;
  request_date: string;
  granted_date: string | null;
  decision_date: string | null;
  revoked_date: string | null;
  rejected_date: string | null;
  expired_date: string | null;
  status: ConsentState;
  relevant_dates: {
    requested_at: string;
    granted_at: string | null;
    rejected_at: string | null;
    revoked_at: string | null;
    expired_at: string | null;
  };
  mobile_number?: string;
};

export type ConsentRequestSummary = RelationshipConsentSummary;

export type HealthcareRelationship = {
  id: string;
  patient: { id: number; full_name: string };
  linked_user: { id: number; full_name: string; role: "provider" | "caregiver" };
  alias: string;
  relationship_type: "provider_patient" | "patient_caregiver";
  relationship_status: "ACTIVE" | "INACTIVE";
  consent_request_id: number;
  relationship_date: string;
  deactivated_at: string | null;
  mobile_number?: string;
  created?: boolean;
  deactivated?: boolean;
};

export type RelationshipListResult = { relationships: HealthcareRelationship[] };
export type LinkablePatientsResult = {
  patients: Array<{
    patient: { id: number; full_name: string };
    consent_request_id: number;
    consent_type: ConsentType;
    granted_at: string;
  }>;
};
export type PatientSearchResult = {
  patient: { id: number; full_name: string };
  consent_status: ConsentState | null;
};

export type ProviderTerm = {
  conceptId: string;
  term: string;
  tag: "medication" | "measurement" | "recommendation" | "investigation";
};

export type AdvisorySummary = {
  id: number;
  advisory_type: ProviderTerm["tag"];
  term: string;
  tag: ProviderTerm["tag"];
  configuration: Record<string, unknown>;
  allergy_warnings: Array<{
    code: string;
    severity: "warning";
    message: string;
    allergen: string;
    blocking: false;
  }>;
  status: "DRAFT" | "PUBLISHED";
  published_at: string | null;
  created_at: string;
};

export type CarePlanSummary = {
  id: number;
  patient: { id: number; full_name: string };
  provider_id: number;
  title: string;
  diagnosis: string | null;
  status: "DRAFT" | "ACTIVE" | "INACTIVE";
  archived_at: string | null;
  advisories: AdvisorySummary[];
  created_at: string;
  updated_at: string;
  event_id?: string;
};

export type PatientAdvisory = {
  id: number;
  advisory_type: ProviderTerm["tag"];
  advisory: string;
  instruction: string;
  status: "PUBLISHED";
  created_at: string;
  published_at: string;
  care_plan: { id: number; title: string; status: "ACTIVE" | "INACTIVE" };
};

export type EventDeliveryStatus = "pending" | "sent" | "acknowledged" | "failed" | "untracked";
export type EventIntegrityStatus = "verified" | "legacy_unverified" | "mismatch";

export type EventMonitorItem = {
  event_id: string;
  event_type: string;
  patient_id: number;
  actor_id: string;
  source: string;
  target: string;
  delivery_status: EventDeliveryStatus;
  retry_count: number;
  occurred_at: string;
  recorded_at: string;
  last_attempt_at: string | null;
  acknowledged_at: string | null;
  delivery_latency_ms: number | null;
  ack_id: string | null;
  received_by: string | null;
  integrity_status: EventIntegrityStatus;
  anomalies: string[];
  payload_preview: Record<string, unknown>;
};

export type EventMonitorDetail = EventMonitorItem & {
  payload: Record<string, unknown>;
  redacted_fields: string[];
  payload_sha256: string;
  lifecycle: Array<{ state: string; timestamp: string }>;
  last_error: { code: string | null; message: string | null } | null;
};

export type EventMonitorSummary = {
  patient_id: number;
  total_events: number;
  delivery_counts: Record<EventDeliveryStatus, number>;
  event_type_counts: Record<string, number>;
  acknowledgement_rate: number;
  average_delivery_latency_ms: number | null;
  latest_event_at: string | null;
  integrity_counts: Record<EventIntegrityStatus, number>;
  anomaly_count: number;
  stale_unacknowledged: number;
  health: "healthy" | "attention";
};

export type EventMonitorPage = {
  events: EventMonitorItem[];
  page: {
    count: number;
    limit: number;
    has_more: boolean;
    next_cursor: string | null;
  };
  filters: Record<string, unknown>;
};

export type ConsentRequestsResult = {
  requests: ConsentRequestSummary[];
};

export type ConsentListResult = {
  consents: RelationshipConsentSummary[];
};

export type ReferenceTermTag = "relationship" | "occupation" | "language" | "gender";

export type ReferenceTerm = {
  conceptId: string;
  term: string;
  tag: ReferenceTermTag;
};
