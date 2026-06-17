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

export type ConsentRequestsResult = {
  requests: ConsentRequestSummary[];
};

export type ConsentListResult = {
  consents: RelationshipConsentSummary[];
};

export type ConsentOtpResult = {
  consent_id: number;
  action: "grant" | "reject" | "revoke";
  otp_sent?: boolean;
  otp_verified?: boolean;
  mobile_number?: string;
};

export type ReferenceTermTag = "relationship" | "occupation" | "language" | "gender";

export type ReferenceTerm = {
  conceptId: string;
  term: string;
  tag: ReferenceTermTag;
};
