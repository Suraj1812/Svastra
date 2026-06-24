# SVASTRA+ MVP API Contract

Version: 4.1 — Timeline Ledger, Event Registry and Alert Dashboard

Updated: 24 June 2026
Scope: identity, RBAC, consent, relationships, care plans, terminology, advisory scheduling, patient tasks, coded responses, investigation uploads, timeline ledger, clinical alerts, provider dashboard feed, PostOffice and API Event Monitor.

This is the single source of truth shared by backend, frontend, QA, product, and non-technical reviewers.

For a practical frontend/backend handoff of the Care Plan Builder, including screen behavior, situations, exact advisory payloads, patient task responses, upload examples, and QA checks, see `docs/care-plan-builder-advisory-payload-guide.md`.

## 1. What the backend does

In ordinary language, the backend enforces this sequence:

```text
Register and log in with OTP
        ↓
Patient controls access consent
        ↓
ACTIVE consent creates a healthcare relationship
        ↓
Only a linked provider can author care
        ↓
Provider selects an approved clinical term
        ↓
Server resolves its type and validates its fields
        ↓
Provider publishes the advisory
        ↓
Schedule and patient tasks are generated
        ↓
PostOffice validates, routes, stores, and acknowledges every CEP event
        ↓
Patient responds or uploads a report
        ↓
Backend updates execution state and generates alerts when rules are breached
```

Consent and relationship are deliberately separate:

- Consent is the patient's permission.
- Relationship is the operational link used for care access.
- Deactivating a relationship does not revoke consent.
- Revoking consent ends the active operational link so access cannot continue.

## 2. Connection and authentication

Local backend URL: `http://127.0.0.1:8000`

Protected endpoints require this header:

```http
X-Session-Token: <raw-session-token-returned-at-login>
```

Security rules:

- Raw session tokens are returned only to the authenticated client and stored as SHA-256 hashes in the database.
- Sessions expire after the configured TTL and become invalid after logout.
- OTP challenges expire, have a resend cooldown, and stop accepting guesses after the configured attempt limit.
- The local MVP OTP is `123456`; it is development-only and must be replaced by a production OTP provider.
- Consent grant, reject, and revoke do not request a second OTP. They require an OTP-authenticated patient session plus explicit confirmation.
- Request bodies reject undeclared fields.
- API request bodies larger than the configured 1 MiB ceiling are rejected before parsing.
- Investigation uploads use a separate bounded multipart allowance and accept at most 5 MiB.
- Uploaded reports are private, signature-checked PDF/JPEG files stored with random names, `0600` permissions and SHA-256 hashes.
- PostOffice event IDs are immutable: an identical queued replay is idempotent, while changed content under the same ID is rejected.
- Monitor cursors are signed and bound to their original filter set.
- Stored CEP documents have a SHA-256 digest checked whenever the monitor reads them.
- Caregiver event details redact diagnoses, clinical configuration, advisory bodies, and messages.
- IDs, roles, ownership, relationships, consent states, terminology bindings, and legal state transitions are rechecked by the server.
- Schedule generation is capped at 500 tasks per advisory to prevent accidental or hostile resource exhaustion.
- Task responses and attachments are immutable: a task accepts exactly one successful response.

## 3. Standard response envelope

Every successful API response has the same outer shape:

```json
{
  "success": true,
  "data": {},
  "message": "Human-readable result",
  "error": null
}
```

Every error has the same outer shape:

```json
{
  "success": false,
  "data": null,
  "message": null,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [
      {
        "field": "patient_id",
        "message": "Input should be greater than 0",
        "type": "greater_than"
      }
    ],
    "request_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
  }
}
```

Every HTTP response includes `X-Request-ID`. Give this ID to backend engineers when reporting a failed request.

Responses also include `X-Process-Time-Ms`, `Cache-Control: no-store`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, a restrictive referrer policy, and a restrictive permissions policy.

| HTTP status | Error code | Meaning |
| --- | --- | --- |
| `400` | `BAD_REQUEST` | Business rule or state transition failed. |
| `401` | `UNAUTHORIZED` | Session token is missing, invalid, expired, or logged out. |
| `403` | `FORBIDDEN` | User is authenticated but lacks the role, ownership, consent, or relationship. |
| `404` | `NOT_FOUND` | The requested record does not exist or is not visible to this user. |
| `405` | `HTTP_ERROR` | HTTP method is not allowed. |
| `422` | `VALIDATION_ERROR` | Body, path, or query data has the wrong type, range, format, or extra fields. |
| `429` | `HTTP_ERROR` | OTP resend cooldown is still active. |
| `413` | `PAYLOAD_TOO_LARGE` | Request body exceeds the configured API ceiling. |
| `500` | `INTERNAL_SERVER_ERROR` | Unexpected server failure; private details are not exposed. |

## 4. Shared data objects

### ReferenceTerm

Registration dropdown values must be sent exactly as supplied by `data/svp_entry_terms.json`.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `conceptId` | string | Yes | Approved terminology identifier. |
| `term` | string | Yes | Human-readable value. |
| `tag` | string | Yes | `occupation`, `gender`, `language`, or `relationship`. |

### UserSummary

| Field | Type | Meaning |
| --- | --- | --- |
| `id` | positive integer | Internal user identifier. |
| `role` | enum | `provider`, `patient`, or `caregiver`. |
| `full_name` | string | Registered name. |
| `mobile_number` | string | Registered mobile number. |
| `professional_category` | ReferenceTerm or null | Provider occupation. |
| `gender` | ReferenceTerm or null | Patient gender. |
| `preferred_language` | ReferenceTerm or null | Patient/caregiver language. |
| `relationship_to_patient` | ReferenceTerm or null | Caregiver relationship. |

### SessionSummary

| Field | Type | Meaning |
| --- | --- | --- |
| `session_token` | string | Raw bearer token. Returned at registration/login/session validation. |
| `expires_at` | ISO datetime | Session expiry. |
| `is_active` | boolean | Whether the session is active. |

### RelationshipConsent

| Field | Type | Meaning |
| --- | --- | --- |
| `id` | positive integer | Consent request ID. |
| `alias` | string, 1–60 chars | Patient-controlled alias; defaults to requestor name. |
| `registered_full_name` | string | Requestor's registered name. |
| `requestor_role` / `role` | enum | `provider` or `caregiver`. |
| `consent_type` | enum | `provider_access` or `caregiver_access`. |
| `status` | enum | `PENDING`, `ACTIVE`, `REJECTED`, `REVOKED`, or `EXPIRED`. |
| `request_date` | ISO datetime | Request time. |
| `granted_date` | ISO datetime or null | Grant time. |
| `decision_date` | ISO datetime or null | Latest decision time. |
| `relevant_dates` | object | Requested, granted, rejected, revoked, and expired timestamps. |
| `mobile_number` | string | Present only in the consent-detail endpoint. |

### HealthcareRelationship

| Field | Type | Meaning |
| --- | --- | --- |
| `id` | string | Link ID, such as `link_pp_...` or `link_pc_...`. |
| `patient` | object | Patient `id` and `full_name`. |
| `linked_user` | object | Provider/caregiver `id`, name, and role. |
| `alias` | string | Patient name for linked-user view; patient-controlled requestor alias for patient view. |
| `relationship_type` | enum | `provider_patient` or `patient_caregiver`. |
| `relationship_status` | enum | `ACTIVE` or `INACTIVE`. |
| `consent_request_id` | positive integer | ACTIVE consent that authorized creation. |
| `relationship_date` | ISO datetime | Creation/reactivation time. |
| `deactivated_at` | ISO datetime or null | Deactivation time. |
| `mobile_number` | string | Present only in relationship detail. |

### ProviderTerm

| Field | Type | Meaning |
| --- | --- | --- |
| `conceptId` | string | Approved local terminology ID. |
| `term` | string | Provider-facing clinical term. |
| `tag` | enum | `medication`, `measurement`, `recommendation`, or `investigation`. |

### Advisory

| Field | Type | Meaning |
| --- | --- | --- |
| `id` | positive integer | Advisory ID. |
| `advisory_type` / `tag` | enum | Resolved advisory category. |
| `term` | string | Approved clinical term. |
| `configuration` | object | Validated, type-specific configuration. |
| `allergy_warnings` | array | Blocking medication allergy warnings. |
| `status` | enum | `DRAFT` or `PUBLISHED`. |
| `published_at` | ISO datetime or null | Publication time. |
| `created_at` | ISO datetime | Creation time. |

### CarePlan

| Field | Type | Meaning |
| --- | --- | --- |
| `id` | positive integer | Care-plan ID. |
| `patient` | object | Patient `id` and `full_name`. |
| `provider_id` | positive integer | Owning provider. |
| `title` | string, 3–160 chars | Care-plan name. |
| `diagnosis` | object, string, or null | Structured diagnosis `{conceptId, term, notes}` for Week 4 flows. Legacy string is still accepted for older local data. |
| `status` | enum | `DRAFT`, `ACTIVE`, or `INACTIVE` when archived. |
| `archived_at` | ISO datetime or null | Archive time. |
| `advisories` | Advisory array | Draft and published advisories. |
| `created_at`, `updated_at` | ISO datetime | Record times. |

### CEPEvent

Events accepted by `POST /postoffice/send` and internal workflow services use this input structure.

| Field | Type | Validation |
| --- | --- | --- |
| `event_type` | enum | One of the supported events below. |
| `event_id` | string, 8–64 chars | Letters, numbers, `.`, `_`, `:`, `-`; globally idempotent. |
| `timestamp` | timezone-aware ISO datetime | A timezone is mandatory. |
| `source` | string, 2–64 chars | Application/service name. |
| `payload` | object, max 64 KiB | Event-specific fields; must include positive `patient_id` and `actor_id`. |

Stored timeline rows preserve the above fields for backward compatibility and also store the canonical Week 4 CEP envelope:

```json
{
  "header": {
    "event_id": "evt_abc123",
    "event_type": "event.response.log",
    "internal_event_type": "response.log",
    "timestamp": "2026-06-24T10:05:00+05:30",
    "source": "rogi_mitra"
  },
  "context": {
    "patient_id": 41,
    "actor_id": 41,
    "provider_id": 12,
    "episode_id": "care_plan:77",
    "encounter_id": "task:task_abcd",
    "target_app": "mantrana_mitra"
  },
  "body": {
    "task_id": "task_abcd",
    "response_type": "measurement",
    "response_status": "recorded"
  }
}
```

Registered input event types:

```text
consent.request
consent.grant
consent.reject
consent.revoke
relationship.created
relationship.deactivated
schedule.generate
advisory.publish
task.generate
response.log
attachment.upload
alert.trigger
message.send
```

Documented canonical Week 4 event names:

| Canonical name | Internal event type | Meaning |
| --- | --- | --- |
| `event.advisory.publish` | `advisory.publish` | Provider published an advisory/care plan item. |
| `event.schedule.generate` | `schedule.generate` | Backend generated task due times and grace window. |
| `event.task.generate` | `task.generate` | Patient-facing care tasks were delivered. |
| `event.response.log` | `response.log` | Patient submitted a medication, measurement, recommendation or missed response. |
| `event.attachment.upload` | `attachment.upload` | Patient uploaded an investigation report. Passive in MVP; it never creates an alert by itself. |
| `event.alert.trigger` | `alert.trigger` | Rule engine created a clinical alert. |

## 5. Endpoint index

| Area | Method and endpoint | Who can call it |
| --- | --- | --- |
| Health | `GET /` | Public |
| Auth | `POST /auth/otp/send` | Public |
| Auth | `POST /auth/otp/verify` | Public |
| Auth | `POST /auth/register/provider` | OTP-verified mobile |
| Auth | `POST /auth/register/patient` | OTP-verified mobile |
| Auth | `POST /auth/register/caregiver` | OTP-verified mobile |
| Auth | `POST /auth/login` | OTP-verified registered mobile |
| Auth | `POST /auth/session/validate` | Token in body |
| Auth | `POST /auth/logout` | Token in body |
| Me | `GET /me/permissions` | Any session |
| Consent | `GET /consent/current` | Public |
| Consent | `GET /me/consent-status` | Patient |
| Consent | `POST /consent/platform/accept` | Patient |
| Consent | `GET /consent/active` | Patient |
| Consent | `GET /consent/pending` | Patient |
| Consent | `GET /consent/inactive` | Patient |
| Consent | `GET /consent/{consent_id}` | Owning patient |
| Consent | `POST /consent/request` | Provider/caregiver |
| Consent | `POST /consent/request/{id}/grant` | Owning patient |
| Consent | `POST /consent/request/{id}/reject` | Owning patient |
| Consent | `POST /consent/request/{id}/revoke` | Owning patient |
| Consent | `PUT /consent/{id}/alias` | Owning patient |
| Relationships | `GET /relationships/search` | Provider/caregiver |
| Relationships | `GET /relationships/linkable` | Provider/caregiver |
| Relationships | `GET /relationships/patients` | Provider/caregiver |
| Relationships | `GET /relationships/providers` | Patient |
| Relationships | `GET /relationships/caregivers` | Patient |
| Relationships | `POST /relationships/provider-patient` | Provider |
| Relationships | `POST /relationships/patient-caregiver` | Caregiver |
| Relationships | `GET /relationships/{link_id}` | Relationship party |
| Relationships | `DELETE /relationships/{link_id}` | Relationship party |
| Terminology | `GET /terminology/provider-terms` | Provider |
| Terminology | `GET /terminology/provider-terms/{concept_id}` | Provider |
| Terminology | `GET /terminology/provider-terms/{concept_id}/advisory-options` | Provider |
| Terminology | `GET /terminology/response-reasons` | Patient |
| Care plans | `POST /care-plans` | Linked provider |
| Care plans | `GET /care-plans` | Provider owner |
| Care plans | `GET /care-plans/{id}` | Provider owner |
| Care plans | `PUT /care-plans/{id}` | Provider owner |
| Care plans | `DELETE /care-plans/{id}` | Provider owner |
| Advisories | `POST /care-plans/{id}/advisories` | Provider owner |
| Advisories | `PUT /care-plans/{id}/advisories/{advisory_id}` | Provider owner, DRAFT only |
| Advisories | `DELETE /care-plans/{id}/advisories/{advisory_id}` | Provider owner, DRAFT only |
| Advisories | `POST /care-plans/{id}/advisories/{advisory_id}/publish` | Linked provider owner |
| Advisories | `POST /care-plans/{id}/publish` | Linked provider owner |
| Patient care | `GET /me/advisories` | Patient |
| Tasks | `GET /me/tasks` | Patient |
| Tasks | `GET /provider/tasks` | Provider owner with ACTIVE relationship |
| Tasks | `GET /tasks/{task_uid}` | Assigned patient or ACTIVE linked provider |
| Responses | `POST /tasks/{task_uid}/responses` | Assigned patient |
| Reports | `POST /tasks/{task_uid}/upload` | Assigned patient |
| Reports | `GET /attachments/{attachment_uid}` | Assigned patient or ACTIVE linked provider |
| Workflow | `POST /provider/tasks/evaluate-overdue` | Provider owner |
| Dashboard | `GET /provider/dashboard-feed` | Provider owner with ACTIVE relationship |
| Alerts | `GET /provider/alerts` | Provider owner with ACTIVE relationship |
| Alerts | `POST /provider/alerts/{alert_uid}/acknowledge` | Provider owner |
| Allergies | `GET /me/allergies` | Patient |
| Allergies | `POST /me/allergies` | Patient |
| PostOffice | `POST /postoffice/send` | Authorized event actor |
| PostOffice | `POST /postoffice/acknowledge` | Patient or linked party |
| PostOffice | `POST /postoffice/events/{event_id}/retry` | Patient or linked party |
| PostOffice | `GET /postoffice/outbound` | Patient or linked party |
| PostOffice | `GET /postoffice/timeline` | Patient or linked party |
| Event Monitor | `GET /postoffice/monitor/summary` | Patient or ACTIVE linked party |
| Event Monitor | `GET /postoffice/monitor/events` | Patient or ACTIVE linked party |
| Event Monitor | `GET /postoffice/monitor/events/{event_id}` | Patient or ACTIVE linked party |

## 6. Health and authentication APIs

### GET /

Purpose: confirms that the service process is running.

Request body: none. Authentication: none.

Response `data`:

```json
{
  "status": "success",
  "message": "SVASTRA+ Authentication Service Running"
}
```

### POST /auth/otp/send

Purpose: creates a short-lived OTP challenge.

| Body field | Type | Required | Validation |
| --- | --- | --- | --- |
| `mobile_number` | string | Yes | 10–20 characters containing 10–15 digits. |

```json
{
  "mobile_number": "9876543210"
}
```

Response `data`:

```json
{
  "success": true,
  "mobile_number": "9876543210",
  "otp_sent": true,
  "expires_in_seconds": 300,
  "retry_after_seconds": 30
}
```

Errors: `422` invalid mobile; `429` resend requested before cooldown.

### POST /auth/otp/verify

| Body field | Type | Required | Validation |
| --- | --- | --- | --- |
| `mobile_number` | string | Yes | Same number used for send. |
| `otp` | string | Yes | 4–8 characters; must match an unexpired challenge. |

```json
{
  "mobile_number": "9876543210",
  "otp": "123456"
}
```

Response `data`: `{"mobile_number":"9876543210","otp_verified":true}`.

Errors: `400` invalid, expired, consumed, absent, or attempt-blocked OTP.

### POST /auth/register/provider

| Body field | Type | Required | Validation |
| --- | --- | --- | --- |
| `full_name` | string | Yes | Non-empty. |
| `mobile_number` | string | Yes | Freshly OTP verified and globally unique. |
| `email_address` | email | No | Valid email. |
| `professional_category` | ReferenceTerm | Yes | Exact approved `occupation` object. |
| `registration_number` | string | Yes | Non-empty. |
| `hpid_number` | string | No | Optional professional identifier. |
| `terms_accepted` | boolean | Yes | Must be `true`. |

Response: `201`; `data` contains `user`, `session`, and `dashboard_route: "/dashboards/mantrana"`.

### POST /auth/register/patient

| Body field | Type | Required | Validation |
| --- | --- | --- | --- |
| `full_name` | string | Yes | Non-empty. |
| `mobile_number` | string | Yes | Freshly OTP verified and globally unique. |
| `date_of_birth` | `YYYY-MM-DD` | Yes | Valid date. |
| `gender` | ReferenceTerm | Yes | Exact approved `gender` object. |
| `preferred_language` | ReferenceTerm | Yes | Exact approved `language` object. |
| `abha_number` | string | No | Optional. |
| `emergency_contact_name` | string | No | Optional. |
| `emergency_contact_mobile` | string | No | 10–15 digits when present. |
| `terms_accepted` | boolean | Yes | Must be `true`. |
| `unified_consent_accepted` | boolean | Yes | Must be `true`. |

Response: `201`; `data` contains `user`, `session`, `consent`, and `dashboard_route: "/dashboards/rogi"`.

### POST /auth/register/caregiver

| Body field | Type | Required | Validation |
| --- | --- | --- | --- |
| `full_name` | string | Yes | Non-empty. |
| `mobile_number` | string | Yes | Freshly OTP verified and globally unique. |
| `relationship_to_patient` | ReferenceTerm | Yes | Exact approved `relationship` object. |
| `preferred_language` | ReferenceTerm | Yes | Exact approved `language` object. |
| `terms_accepted` | boolean | Yes | Must be `true`. |

Response: `201`; route is `/dashboards/sahay`.

### POST /auth/login

Precondition: call OTP send and OTP verify immediately before login.

Body: `{"mobile_number":"9876543210"}`.

Response: `user`, new `session`, and role-specific `dashboard_route`.

Errors: `400` OTP not verified or no active registered user.

### POST /auth/session/validate

Body: `{"session_token":"<raw-token>"}`.

Response `data` contains `valid: true`, `user`, `session`, and `dashboard_route`.

Errors: `401` invalid, expired, or logged-out token.

### POST /auth/logout

Body: `{"session_token":"<raw-token>"}`.

Response `data`: `{"logged_out":true}`. Repeating logout returns `logged_out: false`.

## 7. RBAC and platform consent APIs

### GET /me/permissions

Authentication: any session.

Response `data`:

```json
{
  "user_id": 12,
  "role": "provider",
  "permissions": [
    {"code":"VIEW_PATIENTS","label":"View Patients"},
    {"code":"CREATE_CARE_PLANS","label":"Create Care Plans"}
  ]
}
```

| Role | Permission codes |
| --- | --- |
| Provider | `VIEW_PATIENTS`, `CREATE_CARE_PLANS`, `VIEW_TIMELINE`, `VIEW_ALERTS`, `REQUEST_PATIENT_ACCESS` |
| Patient | `VIEW_TASKS`, `RESPOND_TO_TASKS`, `VIEW_TIMELINE`, `MANAGE_CONSENT` |
| Caregiver | `VIEW_PATIENT_STATUS`, `VIEW_TIMELINE`, `RECEIVE_NOTIFICATIONS`, `REQUEST_CAREGIVER_ACCESS` |
| Admin | `SYSTEM_ADMINISTRATION` |

### GET /consent/current

Authentication: none. Response contains current `consent_version` and the markdown `document`.

### GET /me/consent-status

Authentication: patient.

Response fields: `patient_id`, `current_consent_version`, `consent_version`, `accepted`, `accepted_at`, `consent_status`, `application_name`, `app_version`.

### POST /consent/platform/accept

Authentication: patient.

| Body field | Type | Required | Default |
| --- | --- | --- | --- |
| `application_name` | string or null | No | Server application name. |
| `app_version` | string or null | No | Server version. |

Response: recorded consent version, accepted time, application, version, and request IP.

Compatibility endpoints `POST /consent/patients/{patient_id}/accept` and `GET /consent/patients/{patient_id}/status` require the same patient session and matching path ID. New frontend code should use the `/me` endpoints.

## 8. Relationship consent APIs

### GET /consent/active

Authentication: patient. Body: none. Response: `{"consents":[RelationshipConsent]}` filtered to `ACTIVE`.

### GET /consent/pending

Authentication: patient. Response: `{"requests":[RelationshipConsent]}` filtered to `PENDING`.

`GET /consent/requests` is a compatibility alias for this endpoint.

### GET /consent/inactive

Authentication: patient. Response contains `REJECTED`, `REVOKED`, and `EXPIRED` consents.

### GET /consent/{consent_id}

Authentication: owning patient. The only consent response that includes the requestor's mobile number.

Errors: `403` another patient's record; `400` record missing in the legacy consent service.

### POST /consent/request

Authentication: provider with `REQUEST_PATIENT_ACCESS`, or caregiver with `REQUEST_CAREGIVER_ACCESS`.

| Body field | Type | Required | Validation |
| --- | --- | --- | --- |
| `patient_id` | positive integer | Yes | Active registered patient. |
| `consent_type` | enum | Yes | Provider must use `provider_access`; caregiver must use `caregiver_access`. |
| `alias` | string up to 60 | No | Defaults to requestor's registered name. |

```json
{
  "patient_id": 21,
  "consent_type": "provider_access",
  "alias": "Primary physician"
}
```

Response: `201` with a `PENDING` RelationshipConsent.

Rules: one `PENDING` or `ACTIVE` request per patient/requestor/type; creates audit and `consent.request` CEP records.

### POST /consent/request/{request_id}/grant

Authentication: owning patient.

Body: `{"confirmed":true}`. The literal value `true` is mandatory.

Legal transition: `PENDING → ACTIVE` only.

Effects:

1. Records patient session ID, previous state, new state, actor, and timestamp in audit.
2. Creates and routes `consent.grant`.
3. Creates the matching provider-patient or patient-caregiver relationship.
4. Creates and routes `relationship.created`.

### POST /consent/request/{request_id}/reject

Body: `{"confirmed":true}`. Legal transition: `PENDING → REJECTED`.

### POST /consent/request/{request_id}/revoke

Body: `{"confirmed":true}`. Legal transition: `ACTIVE → REVOKED`.

Revocation deactivates its operational relationship. A manual relationship deactivation does not perform the reverse operation.

### PUT /consent/{consent_id}/alias

Authentication: owning patient. No OTP.

Body: `{"alias":"Primary physician"}`; trimmed length 1–60.

## 9. Healthcare relationship APIs

### GET /relationships/search

Authentication: provider/caregiver with request permission.

Query: `mobile_number` (exact registered value, 10–20 chars).

Response:

```json
{
  "patient": {"id": 21, "full_name": "Asha Patient"},
  "consent_status": null
}
```

`consent_status` is `PENDING`, `ACTIVE`, or null. Search is exact to reduce patient enumeration.

### GET /relationships/linkable

Authentication: provider/caregiver. Returns ACTIVE consents that do not yet have an active operational link.

Response: `{"patients":[{"patient":{},"consent_request_id":4,"consent_type":"provider_access","granted_at":"..."}]}`.

### GET /relationships/patients

Authentication: provider or caregiver.

| Query | Values | Default |
| --- | --- | --- |
| `status` | `ACTIVE`, `INACTIVE`, `ALL` | `ALL` |
| `include_mobile` | `true`, `false` | `false` |

Response: `{"relationships":[HealthcareRelationship]}` for the authenticated linked user.

`include_mobile=true` is provider-only and requires `status=ACTIVE`. It returns the linked patient's registered mobile number for identity disambiguation in clinical patient selectors. Caregivers cannot use this option, inactive/all-relationship queries cannot expose mobile numbers, and the default response remains privacy-minimized.

### GET /relationships/providers

Authentication: patient. Same `status` query. Returns the patient's provider links.

### GET /relationships/caregivers

Authentication: patient. Same `status` query. Returns the patient's caregiver links.

### POST /relationships/provider-patient

Authentication: provider.

Body: `{"patient_id":21,"confirmed":true}`.

Requires matching ACTIVE `provider_access` consent. Idempotent when already active. Normally grant creates the link automatically; this endpoint supports explicit activation/retry.

### POST /relationships/patient-caregiver

Authentication: caregiver. Same body and behavior, requiring ACTIVE `caregiver_access` consent.

### GET /relationships/{link_id}

Authentication: patient/provider/caregiver who is a party to this link. Returns mobile number in addition to HealthcareRelationship.

### DELETE /relationships/{link_id}

Authentication: either party. Body: none.

Effect: `ACTIVE → INACTIVE`, records `relationship.deactivated`, stops access, and leaves consent unchanged.

## 10. Terminology APIs

### GET /terminology/provider-terms

Authentication: provider.

| Query | Type | Required | Validation |
| --- | --- | --- | --- |
| `query` | string | Yes | 3–80 chars. |
| `tag` | advisory-type enum | No | Optional category filter. |
| `limit` | integer | No | 1–20; default 20. |

Response: `{"terms":[ProviderTerm],"query":"temp","count":2}`.

Minimum Friday data includes Paracetamol, Body Temperature, Blood Pressure, Walking Exercise, and HbA1c. Additional demonstration synonyms may also be present.

The approved drug-catalog sample is also indexed. It currently adds Levaz 500 mg oral tablet and Loxof OZ 250 mg + 500 mg oral tablet. Search results expose only the human-readable term and category in the clinician UI; `conceptId` remains an API/storage binding and is never shown as clinical content.

### GET /terminology/provider-terms/{concept_id}

Authentication: provider. Returns the exact ProviderTerm or `404`.

The advisory API never trusts a frontend tag. It verifies that `concept_id`, `term`, and `tag` belong together in the local terminology database.

### GET /terminology/provider-terms/{concept_id}/advisory-options

Authentication: provider. Purpose: gives the frontend the exact server-owned controls for one selected approved term. The frontend must not maintain a separate unit/route/frequency ruleset.

Response `data`:

```json
{
  "term": {
    "conceptId": "2647801000189105",
    "term": "Levaz 500 mg oral tablet",
    "tag": "medication"
  },
  "options": {
    "frequencies": [{"value":"once_daily","label":"Once daily"}],
    "duration_units": ["hours", "days", "weeks", "months"],
    "notifications": ["immediate", "daily_summary", "both", "none"],
    "dose_units": ["tablet"],
    "routes": ["oral"],
    "medication_details": {
      "generic": "Levofloxacin",
      "strength": "500 mg per 1 Tablet",
      "dose_form": "Tablet",
      "route": "Oral",
      "supplier_name": "Hauz Pharma Private Limited"
    }
  }
}
```

Measurement responses instead include `measurement_units` and `comparators`; investigation includes `priorities`. Unknown concepts return `404`; approved measurements with missing unit metadata return `400` and cannot be authored.

### GET /terminology/response-reasons

Authentication: patient. Returns approved coded reasons for a missed response. Optional `query` requires 2–80 characters; `limit` is 1–50.

```json
{
  "reasons": [
    {"conceptId":"422587007","term":"Nausea","tag":"response_reason"},
    {"conceptId":"418290006","term":"Itching","tag":"response_reason"}
  ],
  "count": 2
}
```

The API stores a reason only after rechecking the exact concept/term pair. Free-text medication-miss reasons are rejected.

## 11. Care-plan APIs

### POST /care-plans

Authentication: provider with an ACTIVE consent-backed link to the patient.

| Body field | Type | Required | Validation |
| --- | --- | --- | --- |
| `patient_id` | positive integer | Yes | Must be actively linked to provider. |
| `title` | string | Yes | 3–160 chars. |
| `diagnosis` | object, string, or null | No | Preferred Week 4 object: `{conceptId, term, notes}`. `conceptId` is 1–64 safe chars, `term` is 2–160 chars, `notes` is optional up to 500 chars. Legacy string remains accepted up to 255 chars. |

Response: `201` CarePlan with `DRAFT` status.

### GET /care-plans

Authentication: provider. Optional query `patient_id` filters owned plans. A provider never receives another provider's plans.

Response: `{"care_plans":[CarePlan]}`.

### GET /care-plans/{care_plan_id}

Authentication: owning provider. Returns one CarePlan.

### PUT /care-plans/{care_plan_id}

Authentication: owning provider. Archived plans cannot be updated.

Body:

```json
{
  "title": "Post-operative monitoring",
  "diagnosis": {
    "conceptId": "54150009",
    "term": "Upper Respiratory Tract Infection",
    "notes": "Cough and fever monitoring"
  }
}
```

### DELETE /care-plans/{care_plan_id}

Authentication: owning provider. Archives rather than physically deletes.

Response status becomes `INACTIVE`; published advisory history remains available to the patient.

## 12. Advisory APIs and type-specific bodies

### POST /care-plans/{care_plan_id}/advisories

Authentication: owning provider. Requires a non-archived plan and an approved terminology binding.

Common body:

```json
{
  "concept_id": "demo_term_body_temperature",
  "term": "Body Temperature",
  "tag": "measurement",
  "configuration": {}
}
```

Common configuration fields:

| Field | Type | Required | Validation |
| --- | --- | --- | --- |
| `frequency` | enum | Yes | `once_daily`, `twice_daily`, `three_times_daily`, `four_times_daily`, `every_4_hours`, `every_6_hours`, `weekly`, `monthly`, `as_needed`. |
| `duration_value` | integer | Yes | 1–365. |
| `duration_unit` | enum | Yes | `hours`, `days`, `weeks`, `months`. |
| `additional_instructions` | string | No | Up to 500 chars. |
| `non_response_warning` | object | No | `clinical_grace_minutes` 1–1440, optional `notification`, and optional `severity`. The overdue evaluator runs this rule and suppresses duplicate alerts. |

Medication adds:

| Field | Type | Required | Validation |
| --- | --- | --- | --- |
| `dose_value` | number | Yes | Finite, greater than 0, maximum 1,000,000. Booleans, text, zero, negative, infinity and NaN fail. |
| `dose_unit` | enum | Yes | Must equal the approved drug-catalogue dose form for the selected medication. |
| `route` | enum | Yes | Must equal the approved drug-catalogue route for the selected medication. |

```json
{
  "concept_id": "demo_term_paracetamol",
  "term": "Paracetamol",
  "tag": "medication",
  "configuration": {
    "dose_value": 500,
    "dose_unit": "mg",
    "route": "oral",
    "frequency": "twice_daily",
    "duration_value": 3,
    "duration_unit": "days"
  }
}
```

Only medication concepts present in the approved local drug catalogue are returned by provider search or accepted for new medication advisories. Dose form, route and administration method are catalogue-derived. Medication creation checks the patient's ACTIVE allergy list against both the product term and its catalogue generic ingredient names. A match returns a blocking `allergy_warnings` entry. Publication then creates a critical `allergy_conflict` alert and `alert.trigger` CEP, writes an audit entry, and rejects publication. No schedule, task or `advisory.publish` event is created for the unsafe medicine.

Measurement adds:

| Field | Type | Required | Validation |
| --- | --- | --- | --- |
| `measurement_unit` | string | Yes | Constrained by selected term: temperature `°C/°F`, blood pressure `mmHg`. |
| `value_warning` | object | No | `condition`, numeric `threshold_value`, same `measurement_unit`, optional `notification`, and optional `severity`. |

Allowed `condition`: `more_than`, `less_than`, `at_least`, `at_most`, `equal_to`. Allowed `notification`: `immediate`, `daily_summary`, `both`, `none`; it defaults to `immediate`. Allowed `severity`: `low`, `medium`, `high`, `critical`; value warnings default to `high` and non-response warnings default to `medium`. A value warning using a different unit from the selected measurement is rejected.

Recommendation adds no forced duplicate instruction field: the selected approved term is the recommendation. The provider may add `additional_instructions` in the common fields.

Investigation adds:

| Field | Type | Required | Validation |
| --- | --- | --- | --- |
| `priority` | enum | Yes | `routine`, `urgent`, `asap`, `stat`. |
| `due_date` | ISO date | Yes | Today through five years ahead. |
| `upload_required` | true | Yes/default | Must remain true for the report workflow. |
| `alert_if_not_uploaded` | boolean | No | Defaults true. |
| `grace_period_value` | integer | No | 0–30. |
| `grace_period_unit` | enum | No | `hours` or `days`; defaults `days`. |

Unknown configuration fields, mismatched units, missing fields, duplicate terms in one plan, and tampered terminology all return `400` or `422`.

Created advisory response fields:

| Field | Type | Meaning |
| --- | --- | --- |
| `id` | positive integer | Internal advisory reference. |
| `concept_id` | string | Internal approved terminology identifier returned for draft edit plumbing; do not show to normal users. |
| `advisory_type`, `tag` | enum | Resolved clinical category. |
| `term` | string | Human-readable approved term. |
| `configuration` | object | Normalized validated configuration; unknown fields are absent because they are rejected. |
| `allergy_warnings` | array | Blocking medication warnings; empty for no match/non-medication. |
| `status` | enum | `DRAFT` or `PUBLISHED`. |
| `execution_status` | enum | Server-owned: `pending`, `completed`, `completed_late`, or `missed`. Clients cannot submit or directly alter it. |
| `created_at`, `published_at` | datetime/null | Server timestamps. |

Security and consistency checks occur when the advisory is authored, updated, deleted, and again when its CEP is published. The server rechecks plan ownership, non-archived state, active consent-backed relationship, terminology identity, type-specific schema, units, duplicate concept, stored advisory ownership, publication state, and immutable event fields. Creation, draft update, draft delete, and publication each write an audit entry.

### PUT /care-plans/{care_plan_id}/advisories/{advisory_id}

Authentication: owning provider. Only `DRAFT` advisories can be edited. Published advisories are read-only and return `400`.

Body is the same as `POST /care-plans/{care_plan_id}/advisories`, using the selected approved `concept_id`, exact `term`, exact `tag`, and type-specific `configuration`.

This endpoint exists for the Care Plan Builder `Ready to send` section. It must not be used for already sent/published advisories.

### DELETE /care-plans/{care_plan_id}/advisories/{advisory_id}

Authentication: owning provider. Only `DRAFT` advisories can be deleted. Published advisories are read-only and return `400`.

Response:

```json
{
  "advisory_id": 8,
  "care_plan_id": 3,
  "patient_id": 41,
  "advisory_type": "measurement",
  "deleted": true
}
```

### POST /care-plans/{care_plan_id}/advisories/{advisory_id}/publish

Authentication: owning provider with an ACTIVE relationship at publication time.

Body: `{"confirmed":true}`.

Effects:

1. Advisory becomes immutable `PUBLISHED`.
2. The bounded schedule is calculated and stored as patient tasks.
3. Care plan becomes `ACTIVE`; advisory starts at `execution_status: pending`.
4. Creates ordered `schedule.generate`, `advisory.publish`, and `task.generate` CEPs.
5. PostOffice validates stored ownership/state and routes every event.
6. Receiver copies and acknowledgements are stored.
7. Successful temporary outbound rows are removed.
8. Schedule, task, publication and delivery audit records remain.

Exact `advisory.publish` CEP body stored in the immutable timeline:

```json
{
  "event_type": "advisory.publish",
  "event_id": "evt_018f4f457d5d4b4ea68967262f887123",
  "timestamp": "2026-06-21T10:00:00Z",
  "source": "mantrana_mitra",
  "payload": {
    "actor_id": 12,
    "patient_id": 41,
    "care_plan_id": 3,
    "title": "Recovery monitoring",
    "diagnosis": {
      "conceptId": "54150009",
      "term": "Upper Respiratory Tract Infection",
      "notes": "Cough and fever monitoring"
    },
    "execution_status": "pending",
    "advisories": [
      {
        "advisory_id": 8,
        "advisory_type": "measurement",
        "concept_id": "demo_term_body_temperature",
        "term": "Body Temperature",
        "tag": "measurement",
        "execution_status": "pending",
        "configuration": {
          "frequency": "four_times_daily",
          "duration_value": 5,
          "duration_unit": "days",
          "measurement_unit": "°F",
          "additional_instructions": "Record after resting for five minutes"
        }
      }
    ]
  }
}
```

The CEP validator requires top-level and per-advisory `execution_status` to be exactly `pending`, a non-empty concept/term, a supported advisory type, a non-empty configuration object, and no more than 50 advisories. The dispatcher then compares the event with the stored published advisory before accepting delivery.

Response:

```json
{
  "advisory": {},
  "event_id": "evt_...",
  "acknowledgement": {
    "ack_id": "ack_...",
    "event_id": "evt_...",
    "received_by": "rogi_mitra",
    "status": "received",
    "received_at": "2026-06-19T10:00:00Z"
  }
}
```

### POST /care-plans/{care_plan_id}/publish

Compatibility/bulk action. Body: `{"confirmed":true}`. Publishes every remaining DRAFT advisory as its own CEP and acknowledgement.

Response adds `event_id`, `event_ids`, and `deliveries` to CarePlan.

### GET /me/advisories

Authentication: patient. Read-only Friday view.

Response:

```json
{
  "advisories": [
    {
      "id": 8,
      "advisory_type": "measurement",
      "advisory": "Body Temperature",
      "instruction": "Record Body Temperature in °F (four times daily) for 5 days. Record after resting for five minutes",
      "status": "PUBLISHED",
      "execution_status": "pending",
      "created_at": "2026-06-19T09:00:00Z",
      "published_at": "2026-06-19T09:05:00Z",
      "care_plan": {"id":3,"title":"Recovery monitoring","status":"ACTIVE"}
    }
  ]
}
```

`instruction` is a patient-friendly sentence generated by the backend from the validated configuration. The task screen is the actionable surface; My Advisories remains read-only history.

## 13. Schedule, task, response, report and alert APIs

### Schedule rules

Publication generates tasks from the validated frequency and duration.

| Frequency | Interval |
| --- | --- |
| `once_daily` | 24 hours |
| `twice_daily` | 12 hours |
| `three_times_daily` | 8 hours |
| `four_times_daily` | 6 hours |
| `every_4_hours` | 4 hours |
| `every_6_hours` | 6 hours |
| `weekly` | 168 hours |
| `monthly` | 720 hours for MVP scheduling |
| `as_needed` | One task |

Hours, days, weeks and months convert to 1, 24, 168 and 720 hours. More than 500 generated tasks is rejected before publication. Investigation creates one task due at 17:00 UTC on `due_date`.

### CareTask object

| Field | Type | Meaning |
| --- | --- | --- |
| `task_id` | opaque string | Server-generated task reference; never manufactured by clients. |
| `advisory_id`, `care_plan_id` | positive integer | Parent records. |
| `task_type` | enum | `medication`, `measurement`, `recommendation`, `investigation`. |
| `patient` | object | Patient ID/name visible only inside authorized scope. |
| `title`, `advisory` | string | Simple patient instruction and approved term. |
| `configuration` | object | Validated advisory configuration. |
| `expected_response` | enum | `taken_or_missed`, `numeric_value`, `done_or_missed`, `report_upload`. |
| `due_at`, `grace_expires_at` | datetime | Due and clinical grace boundary. |
| `execution_status` | enum | `pending`, `completed`, `completed_late`, `missed`. |
| `response` | object/null | Immutable response after completion. |

### GET /me/tasks

Authentication: patient. Optional `execution_status` filter. Returns at most 500 assigned tasks ordered by due time.

### GET /provider/tasks

Authentication: provider. Optional `patient_id` and `execution_status`. Only tasks belonging to currently ACTIVE consent-backed relationships are returned.

### GET /tasks/{task_uid}

Authentication: assigned patient or owning provider with an ACTIVE relationship. Task IDs must match `task_` plus 32 lowercase hexadecimal characters.

### POST /tasks/{task_uid}/responses

Authentication: assigned patient. Status: `201`. Unknown fields are rejected. Only a `pending` task without a response can be submitted.

Common body fields:

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `response_status` | enum | Yes | Type-specific values below. |
| `reason` | coded object/null | Conditional | Allowed only for `missed`; mandatory for missed medication. |
| `numeric_value` | finite number/null | Measurement | −1,000,000 to 1,000,000. |
| `measurement_unit` | string/null | Measurement | Must exactly match the advisory unit. |

Medication taken:

```json
{"response_status":"taken"}
```

Medication missed:

```json
{
  "response_status": "missed",
  "reason": {"concept_id":"422587007","term":"Nausea"}
}
```

Measurement:

```json
{
  "response_status": "recorded",
  "numeric_value": 101.2,
  "measurement_unit": "°F"
}
```

Recommendation accepts `done` or `missed`. Investigation accepts `missed` here; a successful investigation uses the upload endpoint.

Successful processing:

1. Stores one immutable TaskResponse.
2. Sets task status to `completed`, `completed_late`, or `missed` using the grace boundary.
3. Recalculates aggregate advisory status.
4. Creates, routes and acknowledges `response.log`.
5. Evaluates any measurement threshold.
6. Creates `value_threshold` alert + `alert.trigger` only when the configured rule is breached and notification is not `none`.
7. Writes mandatory response audit history.

### POST /tasks/{task_uid}/upload

Authentication: assigned patient. Content type: `multipart/form-data`; form field: `file`.

Validation:

| Rule | Accepted |
| --- | --- |
| Task | Pending investigation only |
| File type | PDF or JPEG only |
| MIME | `application/pdf` or `image/jpeg` |
| Content signature | `%PDF-` or JPEG `FF D8 FF`; extension alone is never trusted |
| Maximum | 5 MiB plus bounded multipart overhead |
| Filename | Basename only, 1–180 chars, PDF/JPG/JPEG extension |
| Storage | Private directory, random server filename, `0600` permission |
| Integrity | SHA-256 recorded and returned in `X-Content-SHA256` on download |

The database write, `response.log`, `attachment.upload` event and file are coordinated. If event/database persistence fails, the new private file is removed. Investigation upload is passive in the MVP: upload success or upload absence does not create a clinical alert unless a future document explicitly adds that rule.

### GET /attachments/{attachment_uid}

Returns the binary report only to the assigned patient or owning provider with a currently ACTIVE consent-backed relationship. Other providers receive `403`. The storage path is never returned.

### POST /provider/tasks/evaluate-overdue

Authentication: provider. Body:

```json
{"patient_id": 41}
```

`patient_id` may be null to evaluate all actively linked patients. At most 500 overdue pending tasks are evaluated per call. Each becomes `missed`. Only measurement and recommendation tasks can create non-response alerts today. Investigation tasks remain passive in the MVP, even when `alert_if_not_uploaded` exists in older payloads. A second evaluation does not duplicate terminal tasks or alerts.

### GET /provider/dashboard-feed

Authentication: provider. Optional query: `patient_id`.

Purpose: one lightweight provider dashboard feed for status indicators and summary cards.

Response `data`:

```json
{
  "active_alerts": [
    {
      "alert_id": "alert_123",
      "alert_type": "value_threshold",
      "severity": "critical",
      "display": {
        "title": "Temperature Above Threshold",
        "reason": "threshold_exceeded",
        "concept": "Temperature",
        "recorded_value": "102.5 °F",
        "status_label": "Open Alert"
      }
    }
  ],
  "recent_responses": [
    {
      "task_id": "task_abc",
      "advisory": "Temperature",
      "execution_status": "completed",
      "response": {
        "response_status": "recorded",
        "value": {
          "numeric_value": 102.5,
          "measurement_unit": "°F"
        }
      }
    }
  ],
  "patient_status": [
    {
      "patient": {"id": 41, "full_name": "Rahul Sharma"},
      "status": "alert_present",
      "label": "Alert Present",
      "color": "red",
      "open_alert_count": 1,
      "recent_response_count": 1,
      "overdue_pending_count": 0
    }
  ]
}
```

Status indicator rules:

| Label | Color | Meaning |
| --- | --- | --- |
| `Stable` | green | No open alert and nothing waiting for review. |
| `Pending Review` | yellow | Recent response or overdue pending item exists but no open alert. |
| `Alert Present` | red | At least one open alert exists for the patient. |

### GET /provider/alerts

Authentication: provider. Optional `patient_id` and `alert_status=OPEN|ACKNOWLEDGED`. Only alerts within ACTIVE consent-backed relationships are returned.

Alert object fields:

| Field | Meaning |
| --- | --- |
| `alert_id`, `advisory_id`, `task_id` | Stored references. |
| `patient`, `advisory` | Human-readable context. |
| `alert_type` | `allergy_conflict`, `non_response`, or `value_threshold`. |
| `severity` | `low`, `medium`, `high`, or `critical`. |
| `message` | Safe clinical summary. |
| `notification_mode` | `immediate`, `daily_summary`, or `both`. `none` suppresses rule-generated alerts. |
| `status` | `OPEN` or `ACKNOWLEDGED`. |
| `display` | Non-technical alert UI helper: title, reason, concept, recorded value, and Open/Resolved label. |
| `event_id`, timestamps | CEP and lifecycle references. |

### POST /provider/alerts/{alert_uid}/acknowledge

Authentication: owning provider with ACTIVE relationship. Body: `{"confirmed":true}`. Idempotent; returns `changed: false` when already acknowledged. Writes `alert.acknowledged` audit history.

### Aggregate advisory status

| Task state | Advisory result |
| --- | --- |
| Any task still pending | `pending` |
| All terminal and any missed | `missed` |
| All terminal, none missed, any late | `completed_late` |
| All tasks completed on time | `completed` |

## 14. Allergy APIs

### GET /me/allergies

Authentication: patient. Response: `{"allergies":[{"id":1,"allergen_term":"Paracetamol","status":"ACTIVE","created_at":"..."}]}`.

### POST /me/allergies

Authentication: patient only.

| Body field | Type | Required | Validation |
| --- | --- | --- | --- |
| `allergen_term` | string | Yes | Trimmed length 2–160. |

Idempotent for an existing case-insensitive allergen. Providers cannot silently modify a patient's allergy list.

## 15. PostOffice APIs

### POST /postoffice/send

Authentication: event actor. Status: `202 Accepted`.

Example message event:

```json
{
  "event_type": "message.send",
  "event_id": "evt_018f4f457d5d4b4ea68967262f887123",
  "timestamp": "2026-06-19T10:00:00+05:30",
  "source": "mantrana_mitra",
  "payload": {
    "patient_id": 21,
    "actor_id": 12,
    "message_id": "msg_001",
    "message_text": "Please repeat the temperature after 30 minutes."
  }
}
```

Authorization rules:

- `payload.actor_id` must match authenticated user.
- Patient may send only for self.
- Provider/caregiver clinical events require an ACTIVE consent-backed relationship.
- Consent, relationship, and advisory events must match the stored domain record and status.
- Reusing an event ID while still queued is idempotent and returns `duplicate: true`.

Response fields: `event_id`, `patient_id`, `target_app`, `status`, `retry_count`, timestamps, `handler`, and `duplicate`.

### POST /postoffice/acknowledge

Body:

```json
{
  "event_id": "evt_018f4f457d5d4b4ea68967262f887123",
  "received_by": "rogi_mitra",
  "status": "received"
}
```

Rules: event must be `sent`; `received_by` must equal routed target; status must be literal `received`; caller must have patient scope.

Effect: stores receiver copy and acknowledgement, writes audit, removes only temporary queue row. Permanent event history remains.

### POST /postoffice/events/{event_id}/retry

Authentication: patient or ACTIVE linked user for event patient. Body: none.

Sets pending, increments retry count, updates last attempt, and routes again.

### GET /postoffice/outbound

Required query: `patient_id` positive integer. Returns at most 100 newest pending/sent queue records visible to caller.

### GET /postoffice/timeline

Required query: `patient_id`. Returns at most 100 newest immutable CEP history records visible to caller.

This endpoint powers the Week 4 clinical Timeline UI. It returns human-friendly labels plus the canonical CEP for engineers.

Provider example after Temperature `102.5 °F`:

```json
{
  "events": [
    {
      "event_id": "evt_alert",
      "event_type": "event.alert.trigger",
      "internal_event_type": "alert.trigger",
      "label": "Temperature Above Threshold",
      "timestamp": "2026-06-24T10:06:00+05:30",
      "source": "rogi_mitra",
      "source_label": "Patient App",
      "patient_id": 41,
      "provider_id": 12,
      "episode_id": "advisory:99",
      "encounter_id": "alert:alert_123",
      "details": {
        "Event Type": "event.alert.trigger",
        "Source": "Patient App",
        "Reason": "threshold_exceeded",
        "Concept": "Temperature",
        "Recorded Value": "102.5 °F",
        "Severity": "critical"
      },
      "cep": {
        "header": {},
        "context": {},
        "body": {}
      }
    }
  ]
}
```

Role wording:

| Same backend event | Provider label | Patient label |
| --- | --- | --- |
| `event.advisory.publish` | `Advisory Published` | `Care Plan Received` |
| `event.task.generate` | `Care Plan Delivered` | `Care Plan Delivered` |
| `event.response.log` measurement | `Temperature Received` | `Temperature Submitted` |
| `event.attachment.upload` investigation | `CBC Uploaded` | `CBC Uploaded` |
| `event.response.log` recommendation done | `Steam Inhalation Completed` | `Steam Inhalation Completed` |
| `event.alert.trigger` threshold | `Temperature Above Threshold` | `Temperature Above Threshold` |

Selecting an event in the UI shows only:

- Event Type
- Timestamp
- Source
- Event Details

## 16. API Event Monitor

The API Event Monitor is the secured technical operational view for engineers. The normal Timeline tab uses `GET /postoffice/timeline`; the monitor endpoints report PostOffice transport state, queue state, acknowledgement state, and payload integrity. They do not create healthcare tasks or make clinical decisions.

### Access boundary

- A patient may monitor only their own events.
- A provider may monitor a patient only while an ACTIVE provider-patient link and its source consent remain ACTIVE.
- A caregiver has the same relationship requirement, but sensitive clinical payload fields are redacted.
- Providers and caregivers see only events they authored or events whose immutable payload explicitly identifies them as the related requestor/linked user. An active relationship never exposes another professional's event stream.
- Event IDs never grant access by themselves. Detail lookup also requires `patient_id`, and the server checks the relationship before looking up the event within that scope.
- Revoking consent or deactivating the link immediately removes provider/caregiver monitor access.

### Delivery states

| State | Meaning |
| --- | --- |
| `pending` | Event is durably queued but has not completed a send attempt. |
| `sent` | At least one bounded delivery attempt was made; acknowledgement is pending. |
| `acknowledged` | Receiver copy and immutable acknowledgement both exist; the temporary queue row is removed. |
| `failed` | Latest delivery attempt failed and contains a safe error code/message. |
| `untracked` | Timeline event has neither queue row nor acknowledgement. This is an anomaly requiring investigation. |

Integrity is reported independently as `verified`, `legacy_unverified`, or `mismatch`. `mismatch` means the stored CEP no longer matches its SHA-256 digest and must be treated as an incident.

### Shared monitor filters

| Query field | Type | Required | Validation and behavior |
| --- | --- | --- | --- |
| `patient_id` | positive integer | Yes | Patient scope is re-authorized on every call. |
| `event_type` | CEP event enum | No | Exact match; arbitrary event names are rejected. |
| `delivery_status` | delivery-state enum | No | Exact derived transport status. |
| `source` | string | No | 2–64 chars; letters, numbers, dot, underscore and hyphen. |
| `target` | string | No | Same rules as source. |
| `event_id_prefix` | string | No | 3–64 allowed event-ID characters; prefix search only. |
| `occurred_from` | timezone-aware datetime | No | Inclusive lower bound. |
| `occurred_to` | timezone-aware datetime | No | Inclusive upper bound. |

When both time bounds are present, `occurred_from` must precede `occurred_to`, and the interval cannot exceed `MONITOR_MAX_WINDOW_DAYS` (366 by default). Unknown query fields return `422`.

### GET /postoffice/monitor/summary

Authentication: patient or ACTIVE linked provider/caregiver.

Accepts the shared filters. Response fields:

| Field | Type | Meaning |
| --- | --- | --- |
| `patient_id` | integer | Authorized patient scope. |
| `total_events` | integer | Events matching current filters. |
| `delivery_counts` | object | Counts for pending, sent, acknowledged, failed and untracked. |
| `event_type_counts` | object | Count per CEP type. |
| `acknowledgement_rate` | number | Acknowledged events divided by matching events, percentage. |
| `average_delivery_latency_ms` | number or null | Mean timeline-record to acknowledgement duration. |
| `latest_event_at` | datetime or null | Latest matching business timestamp. |
| `integrity_counts` | object | Verified, legacy-unverified and mismatch totals. |
| `anomaly_count` | integer | Count of integrity/delivery anomaly signals. |
| `stale_unacknowledged` | integer | Queue items still open after five minutes. |
| `health` | enum | `healthy` or `attention`. |

Example:

```json
{
  "patient_id": 3,
  "total_events": 7,
  "delivery_counts": {
    "pending": 0,
    "sent": 6,
    "acknowledged": 1,
    "failed": 0,
    "untracked": 0
  },
  "acknowledgement_rate": 14.29,
  "average_delivery_latency_ms": 23.4,
  "integrity_counts": {"verified": 7, "legacy_unverified": 0, "mismatch": 0},
  "anomaly_count": 0,
  "stale_unacknowledged": 0,
  "health": "healthy"
}
```

### GET /postoffice/monitor/events

Authentication: patient or ACTIVE linked provider/caregiver.

Adds these pagination fields to the shared filters:

| Query field | Type | Required | Validation |
| --- | --- | --- | --- |
| `limit` | integer | No | Default 25; range 1–100. |
| `cursor` | string | No | Signed opaque cursor returned by the previous page. |

The query uses `(occurred_at, id)` keyset pagination and the patient/time/type indexes. The cursor is HMAC-signed and contains a filter fingerprint; changing the cursor or filters returns `400`.

Each list item contains:

| Field | Meaning |
| --- | --- |
| `event_id`, `event_type`, `patient_id`, `actor_id` | Event identity and scope. |
| `source`, `target` | PostOffice route. |
| `delivery_status`, `retry_count` | Current derived state and bounded attempt count. |
| `occurred_at`, `recorded_at`, `last_attempt_at`, `acknowledged_at` | Lifecycle timestamps. |
| `delivery_latency_ms` | Record-to-ack duration when acknowledged. |
| `ack_id`, `received_by` | Immutable receipt references when present. |
| `integrity_status` | SHA-256 verification result. |
| `anomalies` | Safe machine-readable anomaly codes. |
| `payload_preview` | Non-sensitive IDs/status summary; full payload is never returned in list pages. |

The `page` object returns `count`, `limit`, `has_more`, and `next_cursor`.

### GET /postoffice/monitor/events/{event_id}

Required query: positive `patient_id`. Event ID must match the CEP ID format.

Returns the list fields plus:

| Field | Meaning |
| --- | --- |
| `payload` | Validated stored payload after role-based recursive redaction. |
| `redacted_fields` | Exact JSON paths replaced by `[REDACTED]`. |
| `payload_sha256` | Stored integrity digest. |
| `lifecycle` | Ordered recorded, sent, received and acknowledged steps that exist. |
| `last_error` | Safe delivery error code/message for a currently queued failed event. |

Opening detail writes `postoffice.monitor_detail_viewed` to the audit log with actor, patient, event, IP and request timestamp. Raw session tokens, OTPs, mobile numbers, IPs and session identifiers are always redacted. Internal `concept_id` values are also redacted for non-provider viewers. Caregivers additionally cannot see `diagnosis`, `advisories`, `configuration`, or `message_text`.

## 17. Event-specific payload validation

| Event family | Additional required payload fields |
| --- | --- |
| `consent.*` | `consent_id`, `requestor_id`, `status` |
| `relationship.*` | `relationship_id`, `linked_user_id`, `relationship_type`, `status` |
| `schedule.generate` | `care_plan_id`, `advisory_id`, positive `task_count` |
| `advisory.publish` | `care_plan_id`, top-level `execution_status=pending`, non-empty `advisories` array; every entry requires advisory ID/type, concept, term, `execution_status=pending`, configuration |
| `task.generate` | `care_plan_id`, `advisory_id`, 1–500 unique task IDs |
| `response.log` | `task_id`, response type/status, terminal execution status; must match stored immutable response |
| `alert.trigger` | `alert_id`, `severity` |
| `message.send` | `message_id`, `message_text` |

## 18. Frontend integration checklist

The frontend must:

1. Store the session token only in the existing auth state and attach `X-Session-Token` to protected calls.
2. Treat `401` as signed out and `403` as insufficient access, not as a generic server error.
3. Send `confirmed: true` only after the user accepts a visible confirmation dialog.
4. Never infer access from UI state; wait for backend success.
5. Search terminology only after three characters.
6. Submit the exact selected `conceptId`, `term`, and `tag`; never manufacture tags and never display concept IDs to clinical users.
7. Fetch `/advisory-options` after selection and render its server-owned controls; show validation messages beside the relevant fields.
8. Display medication allergy conflicts prominently and disable publication until another medicine is selected.
9. Hide mobile numbers in list views; fetch detail endpoints only when the user opens details.
10. Refresh consent, relationship, and care-plan data after every state-changing call.
11. Show `request_id` when support/debug information is useful.
12. Do not expose raw CEP JSON to patients.
13. Use `next_cursor` exactly as returned; never construct or edit monitor cursors.
14. Fetch full monitor payload only after a user explicitly opens event detail.
15. Preserve `[REDACTED]` values and never try to reconstruct caregiver-hidden data client-side.
16. Keep patient task actions short and obvious: Taken, Missed, Done, Save, Choose report, Upload.
17. Never accept a free-text medication-miss reason; submit the selected coded reason.
18. Send uploads as multipart without a JSON `Content-Type` header.
19. Show only one care-plan send action; keep the single-advisory publish API available for integrations, not as a duplicate provider button.
20. For catalog medications, display dose form, route and method as trusted read-only metadata. Do not ask the provider to re-enter them.
21. Show investigation priority as a small constrained choice group and show that report upload is required.
22. Keep notification routing defaults out of the clinical form; the provider chooses the clinical rule and severity, while the backend applies the documented delivery default.

## 19. End-to-end acceptance example

```text
Provider POST /consent/request
Patient POST /consent/request/{id}/grant {confirmed:true}
Backend creates ACTIVE relationship
Provider POST /care-plans
Provider GET /terminology/provider-terms?query=body
Provider GET /terminology/provider-terms/{concept_id}/advisory-options
Provider POST /care-plans/{id}/advisories
Provider reviews any allergy_warnings
Provider POST /care-plans/{id}/advisories/{advisory_id}/publish {confirmed:true}
Backend returns event_id + acknowledgement
Backend records schedule.generate → advisory.publish → task.generate
Patient GET /me/tasks
Patient POST /tasks/{task_uid}/responses or /upload
Backend records response.log, attachment.upload when applicable, and updates task/advisory execution status
Backend optionally records alert.trigger for threshold/non-response rules
Provider GET /provider/dashboard-feed, /provider/tasks and /provider/alerts
Provider/patient opens Timeline and sees the clinical lifecycle
```
