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

`professional_category` must be the exact object from `data/svp_entry_terms.json` where `tag = "occupation"`.

Request:

```json
{
  "full_name": "Dr Meera",
  "mobile_number": "9876543210",
  "professional_category": {
    "conceptId": "309343006",
    "term": "Physician",
    "tag": "occupation"
  },
  "registration_number": "REG-123",
  "terms_accepted": true
}
```

### POST /auth/register/patient

Required fields: `full_name`, `mobile_number`, `date_of_birth`, `gender`, `preferred_language`, `terms_accepted`, `unified_consent_accepted`.

Optional fields: `abha_number`, `emergency_contact_name`, `emergency_contact_mobile`.

`gender` and `preferred_language` must be exact objects from `data/svp_entry_terms.json`.

`unified_consent_accepted` must be `true`.

Request:

```json
{
  "full_name": "Asha Patient",
  "mobile_number": "9876543210",
  "date_of_birth": "1992-05-17",
  "gender": {
    "conceptId": "248152002",
    "term": "Female",
    "tag": "gender"
  },
  "preferred_language": {
    "conceptId": "297487008",
    "term": "English",
    "tag": "language"
  },
  "terms_accepted": true,
  "unified_consent_accepted": true
}
```

### POST /auth/register/caregiver

Required fields: `full_name`, `mobile_number`, `relationship_to_patient`, `preferred_language`, `terms_accepted`.

`relationship_to_patient` and `preferred_language` must be exact objects from `data/svp_entry_terms.json`.

Request:

```json
{
  "full_name": "Ravi Caregiver",
  "mobile_number": "9876543211",
  "relationship_to_patient": {
    "conceptId": "303071001",
    "term": "Family member",
    "tag": "relationship"
  },
  "preferred_language": {
    "conceptId": "161143006",
    "term": "Hindi",
    "tag": "language"
  },
  "terms_accepted": true
}
```

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

Registration, login, and session validation user objects return dropdown selections in the same structure:

```json
{
  "id": 1,
  "role": "patient",
  "full_name": "Asha Patient",
  "mobile_number": "9876543210",
  "professional_category": null,
  "gender": {
    "conceptId": "248152002",
    "term": "Female",
    "tag": "gender"
  },
  "preferred_language": {
    "conceptId": "297487008",
    "term": "English",
    "tag": "language"
  },
  "relationship_to_patient": null
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

## Relationship Consent Management

Wednesday scope implements patient-controlled relationship consent persistence, OTP-authenticated grant/reject/revoke decisions, aliases, audit events, CEP events, and access enforcement.

Supported consent types:

- `provider_access`
- `caregiver_access`

Supported states:

- `PENDING`
- `ACTIVE`
- `REJECTED`
- `REVOKED`
- `EXPIRED`

### POST /consent/request

Requires a provider or caregiver `X-Session-Token`.

Request:

```json
{
  "patient_id": 1,
  "consent_type": "provider_access",
  "alias": "Primary physician"
}
```

`alias` is optional, patient-editable later, and defaults to the registered requestor name.

Response data:

```json
{
  "id": 1,
  "alias": "Dr Meera",
  "registered_full_name": "Dr Meera",
  "requestor_role": "provider",
  "consent_type": "provider_access",
  "request_date": "2026-06-17T08:30:00Z",
  "status": "PENDING"
}
```

Creates audit action `consent.request` and CEP event `consent.request`.

### GET /consent/active

Requires a patient `X-Session-Token`.

Response data:

```json
{
  "consents": [
    {
      "id": 1,
      "alias": "Primary physician",
      "registered_full_name": "Dr Meera",
      "requestor_role": "provider",
      "consent_type": "provider_access",
      "granted_date": "2026-06-17T08:35:00Z",
      "status": "ACTIVE"
    }
  ]
}
```

### GET /consent/pending

Requires a patient `X-Session-Token`.

Response data:

```json
{
  "requests": [
    {
      "id": 1,
      "alias": "Dr Meera",
      "registered_full_name": "Dr Meera",
      "requestor_role": "provider",
      "consent_type": "provider_access",
      "request_date": "2026-06-17T08:30:00Z",
      "status": "PENDING"
    }
  ]
}
```

### GET /consent/inactive

Requires a patient `X-Session-Token`.

Response data:

```json
{
  "consents": [
    {
      "id": 1,
      "alias": "Primary physician",
      "registered_full_name": "Dr Meera",
      "requestor_role": "provider",
      "consent_type": "provider_access",
      "decision_date": "2026-06-17T09:00:00Z",
      "status": "REVOKED"
    }
  ]
}
```

### GET /consent/requests

Requires a patient `X-Session-Token`.

Compatibility alias for `GET /consent/pending`.

### GET /consent/{id}

Requires a patient `X-Session-Token`.

Returns a single relationship consent detail record. `mobile_number` is included only in this details response.

### PUT /consent/{id}/alias

Requires a patient `X-Session-Token`.

Request:

```json
{
  "alias": "Primary physician"
}
```

Alias max length is 60 characters. No OTP is required.

### POST /consent/send-otp

Requires a patient `X-Session-Token`.

Request:

```json
{
  "consent_id": 1,
  "action": "grant"
}
```

Response data:

```json
{
  "consent_id": 1,
  "action": "grant",
  "otp_sent": true,
  "mobile_number": "9876543210"
}
```

### POST /consent/verify-otp

Requires a patient `X-Session-Token`.

Request:

```json
{
  "consent_id": 1,
  "action": "grant",
  "otp": "123456"
}
```

Response data:

```json
{
  "consent_id": 1,
  "action": "grant",
  "otp_verified": true
}
```

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
  "id": 1,
  "status": "ACTIVE"
}
```

Invalid OTP returns `400 BAD_REQUEST`. Creates audit action `consent.grant` and CEP event `consent.grant`.

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
  "id": 1,
  "status": "REJECTED"
}
```

Invalid OTP returns `400 BAD_REQUEST`. Creates audit action `consent.reject` and CEP event `consent.reject`.

### POST /consent/request/{id}/revoke

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
  "id": 1,
  "status": "REVOKED"
}
```

Invalid OTP returns `400 BAD_REQUEST`. Creates audit action `consent.revoke` and CEP event `consent.revoke`.
