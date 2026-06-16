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

export type ConsentRequestSummary = {
  id: string;
  requestor_name: string;
  requestor_role: string;
  consent_type: "provider_access" | "caregiver_access";
  request_date: string;
  status: "PENDING" | "GRANTED" | "REJECTED" | "REVOKED" | "EXPIRED";
};

export type ConsentRequestsResult = {
  requests: ConsentRequestSummary[];
};
