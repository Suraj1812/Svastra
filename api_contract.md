# SVASTRA+ MVP API Contract

All responses use the shared envelope:

```json
{
  "success": true,
  "data": {},
  "message": null,
  "error": null
}
```

Errors use the same envelope with `success: false` and a structured `error` object:

```json
{
  "success": false,
  "data": null,
  "message": null,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [],
    "request_id": "request-id"
  }
}
```

Authenticated endpoints require `X-Session-Token`.

## Authentication

### POST /auth/otp/send

Request:

```json
{
  "mobile_number": "9876543210"
}
```

Response data:

```json
{
  "mobile_number": "9876543210",
  "otp_sent": true,
  "expires_in_seconds": 300
}
```

### POST /auth/otp/verify

Request:

```json
{
  "mobile_number": "9876543210",
  "otp": "123456"
}
```

Response data:

```json
{
  "mobile_number": "9876543210",
  "otp_verified": true
}
```

### POST /auth/register/provider

Required fields: `full_name`, `mobile_number`, `professional_category`, `registration_number`, `terms_accepted`.

Optional fields: `email_address`, `hpid_number`.

### POST /auth/register/patient

Required fields: `full_name`, `mobile_number`, `date_of_birth`, `gender`, `preferred_language`, `terms_accepted`, `unified_consent_accepted`.

Optional fields: `abha_number`, `emergency_contact_name`, `emergency_contact_mobile`.

`unified_consent_accepted` must be `true`.

### POST /auth/register/caregiver

Required fields: `full_name`, `mobile_number`, `relationship_to_patient`, `preferred_language`, `terms_accepted`.

### POST /auth/session/validate

Request:

```json
{
  "session_token": "session-token"
}
```

### POST /auth/logout

Request:

```json
{
  "session_token": "session-token"
}
```

## RBAC

### GET /me/permissions

Requires `X-Session-Token`.

Response data:

```json
{
  "user_id": 1,
  "role": "patient",
  "permissions": [
    {
      "code": "MANAGE_CONSENT",
      "label": "Manage Consent"
    }
  ]
}
```

Permission matrix:

| Role | Permissions |
| --- | --- |
| PROVIDER | VIEW_PATIENTS, CREATE_CARE_PLANS, VIEW_TIMELINE, VIEW_ALERTS, REQUEST_PATIENT_ACCESS |
| PATIENT | VIEW_TASKS, RESPOND_TO_TASKS, VIEW_TIMELINE, MANAGE_CONSENT |
| CAREGIVER | VIEW_PATIENT_STATUS, VIEW_TIMELINE, RECEIVE_NOTIFICATIONS, REQUEST_CAREGIVER_ACCESS |
| ADMIN | SYSTEM_ADMINISTRATION |

Unauthorized sessions return `401 UNAUTHORIZED`. Missing permissions return `403 FORBIDDEN`.

## Platform Consent

### GET /consent/current

Returns the current platform consent version and markdown document.

Response data:

```json
{
  "consent_version": "v1",
  "document": "# SVASTRA+ Unified Platform Consent"
}
```

### GET /me/consent-status

Requires a patient `X-Session-Token`.

Response data:

```json
{
  "patient_id": 1,
  "current_consent_version": "v1",
  "consent_version": "v1",
  "accepted": true,
  "accepted_at": "2026-06-16T08:30:00Z",
  "consent_status": "Accepted",
  "application_name": "SVASTRA+ MVP",
  "app_version": "0.1.0"
}
```

Non-patient sessions return `403 FORBIDDEN`.

### POST /consent/platform/accept

Requires a patient `X-Session-Token`.

Request:

```json
{
  "application_name": "SVASTRA+ MVP",
  "app_version": "0.1.0"
}
```

Both fields are optional; server defaults are used when omitted.

Response data:

```json
{
  "patient_id": 1,
  "consent_version": "v1",
  "accepted_at": "2026-06-16T08:30:00Z",
  "application_name": "SVASTRA+ MVP",
  "app_version": "0.1.0",
  "ip_address": "127.0.0.1"
}
```

## Relationship Consent Foundation

Tuesday scope documents the API surface and validates OTP/session flow. Relationship consent persistence and full decision workflow remain prepared for Wednesday.

Supported consent types:

- `provider_access`
- `caregiver_access`

Supported states:

- `PENDING`
- `GRANTED`
- `REJECTED`
- `REVOKED`
- `EXPIRED`

### GET /consent/requests

Requires a patient `X-Session-Token`.

Response data:

```json
{
  "requests": [
    {
      "id": "request-id",
      "requestor_name": "Dr Meera",
      "requestor_role": "provider",
      "consent_type": "provider_access",
      "request_date": "2026-06-16T08:30:00Z",
      "status": "PENDING"
    }
  ]
}
```

Current Tuesday implementation returns an empty list until Wednesday relationship consent tables are activated.

### POST /consent/request/{id}/grant

Requires a patient `X-Session-Token`.

Request:

```json
{
  "otp": "123456"
}
```

Response data:

```json
{
  "request_id": "request-id",
  "status": "GRANTED",
  "implementation_status": "placeholder_for_wednesday"
}
```

Invalid OTP returns `400 BAD_REQUEST`.

### POST /consent/request/{id}/reject

Requires a patient `X-Session-Token`.

Request:

```json
{
  "otp": "123456"
}
```

Response data:

```json
{
  "request_id": "request-id",
  "status": "REJECTED",
  "implementation_status": "placeholder_for_wednesday"
}
```

Invalid OTP returns `400 BAD_REQUEST`.
