# SVASTRA+ Care Plan Builder and Advisory API Payload Guide

Updated: 26 June 2026

Purpose: this document explains how the Care Plan Builder works end to end, when each screen/API is used, what payload is sent, what response comes back, and what backend validations protect the flow.

Audience: frontend engineers, backend engineers, QA, product reviewers, and non-technical reviewers.

## 1. One-line product meaning

Care Plan Builder lets a provider select an actively linked patient, create or select a care plan, add approved clinical advice, send it to the patient, and then track patient tasks, responses, reports, and alerts.

The backend is the final authority. The frontend should keep the UI simple and send only the fields listed here.

## 2. Who can do what

| User | Allowed in this flow | Not allowed |
| --- | --- | --- |
| Provider | Create/select care plans, add advisories, publish advisories, view linked patient tasks/alerts, acknowledge alerts, download linked investigation reports. | Author for patients without ACTIVE consent-backed relationship, edit another provider's plan, publish unsafe allergy-conflict medication. |
| Patient | View published advisories, view tasks, mark tasks done/taken/missed/recorded, upload investigation report, add own allergy. | Create provider care plans, see provider-only authoring fields, respond for another patient. |
| Caregiver | Relationship/listing features outside this builder. | Author care plans, request mobile numbers through provider builder APIs, view provider clinical authoring payload. |

## 3. Current frontend screen contract

### Step 1: Care plan

The screen has only two modes.

| Mode | UI fields/buttons | Backend source |
| --- | --- | --- |
| Existing plan | `Search or select care plan` dropdown, `New care plan` button. Dropdown label should be `care plan name — patient name — mobile`. | `GET /care-plans` and `GET /relationships/patients?status=ACTIVE&include_mobile=true` |
| New care plan | `Linked patient`, `Care plan name`, `Diagnosis`, optional `Notes`, `Create`, `Cancel`. Patient dropdown label should be `patient name — mobile`. | `POST /care-plans` |

Do not show provider name as an editable/read-only field. The backend already knows the provider from `X-Session-Token`.

Do not show or send `Draft` as an input. The backend creates new plans as `DRAFT`.

Do not show a SNOMED/concept ID field for diagnosis. Diagnosis concept IDs are
internal/imported identifiers and are optional in this flow. Existing stored
diagnosis concept IDs still return from the API, but providers should never
manually type them.

### Step 2: Add advice

The provider searches approved terminology. Search starts after at least 3 characters.

| Advisory type | UI controls |
| --- | --- |
| Medication | Catalog medication only, read-only form/route/method/strength, dose quantity, frequency, duration, optional instruction. |
| Measurement | Measurement unit, frequency, duration, optional value warning, optional non-response alert. |
| Investigation | Priority, report due date, grace period, upload required switch checked ON, alert-if-not-uploaded checkbox, frequency, duration. |
| Recommendation | Frequency, duration, optional instruction. |

The frontend must not invent fields. It should first call advisory options and render only controls returned or supported by that selected type.

### Step 3: Advisories

| Section | Meaning |
| --- | --- |
| Ready to send | Draft advisories that can be published. |
| Published advisories | Already sent advisories; immutable from the authoring UI. |

If any draft advisory has `allergy_warnings`, disable send and show the warning. Backend will also block publication.

Draft advisories in `Ready to send` can be edited or deleted. Published advisories must not show edit/delete controls, and backend rejects edit/delete attempts for them.

## 4. End-to-end situation flow

```text
Provider login
  ↓
Load ACTIVE linked patients with mobile numbers
  ↓
Load provider's care plans
  ↓
Provider selects existing plan OR creates new plan
  ↓
Provider searches approved clinical term
  ↓
Backend returns exact allowed controls for that term
  ↓
Provider adds advisory
  ↓
Backend validates type, term, catalogue, ranges, units, duplicate, allergy
  ↓
Provider sends plan/advisory
  ↓
Backend rechecks ACTIVE relationship, blocks allergy conflict, generates schedule/tasks/events
  ↓
Patient receives tasks and responds/uploads
  ↓
Backend stores immutable response, updates execution status, sends response event, creates alerts if rule breached
  ↓
Provider tracks tasks and alerts
```

## 5. Shared API rules

Base URL in local development: `http://127.0.0.1:8000`

Frontend proxy usually calls paths as `/api/...`.

Protected calls require:

```http
X-Session-Token: <session token from login/register>
```

Success response envelope:

```json
{
  "success": true,
  "data": {},
  "message": "Human-readable message or null",
  "error": null
}
```

Error response envelope:

```json
{
  "success": false,
  "data": null,
  "message": null,
  "error": {
    "code": "BAD_REQUEST",
    "message": "Business rule failed",
    "details": null,
    "request_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
  }
}
```

Common status meaning:

| HTTP status | Meaning |
| --- | --- |
| `400` | Business rule failed: wrong state, duplicate advisory, unsafe allergy conflict, invalid option selected. |
| `401` | Session token missing/invalid/expired. |
| `403` | Wrong role, wrong owner, or no ACTIVE consent-backed relationship. |
| `404` | Record missing or hidden from this user. |
| `422` | Payload shape/range/type is invalid or has extra fields. |

## 6. Load builder screen

### 6.1 Get linked patients with mobile number

Use this only for provider builder dropdowns.

```http
GET /relationships/patients?status=ACTIVE&include_mobile=true
X-Session-Token: <provider-session>
```

Important privacy rule:

- `include_mobile=true` is provider-only.
- `include_mobile=true` requires `status=ACTIVE`.
- Caregiver request with `include_mobile=true` returns `403`.

Sample response:

```json
{
  "success": true,
  "data": {
    "relationships": [
      {
        "id": "provider_patient_1",
        "patient": {
          "id": 10,
          "full_name": "Suraj Singh"
        },
        "linked_user": {
          "id": 2,
          "full_name": "Dr Suraj Rajput",
          "role": "provider"
        },
        "alias": "Suraj Singh",
        "relationship_type": "provider_patient",
        "relationship_status": "ACTIVE",
        "consent_request_id": 44,
        "relationship_date": "2026-06-19T08:00:00Z",
        "deactivated_at": null,
        "mobile_number": "0101010101"
      }
    ]
  },
  "message": null,
  "error": null
}
```

Frontend labels:

- Patient dropdown: `Suraj Singh — 0101010101`
- Care plan dropdown: `Fever plan — Suraj Singh — 0101010101`

### 6.2 Get provider care plans

```http
GET /care-plans
X-Session-Token: <provider-session>
```

Optional filter:

```http
GET /care-plans?patient_id=10
```

Sample response:

```json
{
  "success": true,
  "data": {
    "care_plans": [
      {
        "id": 25,
        "patient": {
          "id": 10,
          "full_name": "Suraj Singh"
        },
        "provider_id": 2,
        "title": "Fever plan",
        "diagnosis": {
          "conceptId": null,
          "term": "Upper Respiratory Tract Infection",
          "notes": "Cough and fever monitoring"
        },
        "status": "DRAFT",
        "archived_at": null,
        "advisories": [],
        "created_at": "2026-06-23T09:00:00Z",
        "updated_at": "2026-06-23T09:00:00Z"
      }
    ]
  },
  "message": null,
  "error": null
}
```

## 7. Create a new care plan

### Request

```http
POST /care-plans
X-Session-Token: <provider-session>
Content-Type: application/json
```

```json
{
  "patient_id": 10,
  "title": "Fever plan",
  "diagnosis": {
    "term": "Viral fever",
    "notes": "Hydration and temperature watch"
  }
}
```

### Request field table

| Field | Type | Required | Validation | Who sets it |
| --- | --- | --- | --- | --- |
| `patient_id` | integer | Yes | Greater than 0; patient must have ACTIVE provider-patient relationship with current provider. | Frontend from linked-patient dropdown. |
| `title` | string | Yes | 3 to 160 characters. | Provider. |
| `diagnosis` | object | Yes for the current UI | `{term, notes, conceptId?}`. `term` is 2–160 chars, `notes` is optional up to 500 chars, and `conceptId` is optional/imported only. | Provider enters term and notes only. |

Do not send `provider_id`, `provider_name`, `status`, `execution_status`, `created_at`, `updated_at`, or manually typed diagnosis SNOMED IDs.

### Success response

```json
{
  "success": true,
  "data": {
    "id": 25,
    "patient": {
      "id": 10,
      "full_name": "Suraj Singh"
    },
    "provider_id": 2,
    "title": "Fever plan",
    "diagnosis": {
      "conceptId": null,
      "term": "Viral fever",
      "notes": "Hydration and temperature watch"
    },
    "status": "DRAFT",
    "archived_at": null,
    "advisories": [],
    "created_at": "2026-06-23T09:00:00Z",
    "updated_at": "2026-06-23T09:00:00Z"
  },
  "message": "Care plan draft created",
  "error": null
}
```

### Main failure cases

| Situation | Response |
| --- | --- |
| Provider has no active relationship with patient | `403`, `Only a consent-backed linked provider can create a care plan` |
| Patient ID is missing/0/string | `422` |
| Title is too short/too long | `422` |
| Extra field sent | `422` |

## 7.1 Edit or delete a Ready-to-send advisory

Only draft advisories can be changed. In the UI these are the cards under `Ready to send`.

### Edit draft advisory

```http
PUT /care-plans/{care_plan_id}/advisories/{advisory_id}
X-Session-Token: <provider-session>
Content-Type: application/json
```

Body is the same as Add advisory:

```json
{
  "concept_id": "demo_term_temperature",
  "term": "Temperature",
  "tag": "measurement",
  "configuration": {
    "frequency": "four_times_daily",
    "duration_value": 2,
    "duration_unit": "days",
    "measurement_unit": "°C"
  }
}
```

Success response returns the updated advisory and message `Draft advisory updated`.

### Delete draft advisory

```http
DELETE /care-plans/{care_plan_id}/advisories/{advisory_id}
X-Session-Token: <provider-session>
```

Success response:

```json
{
  "success": true,
  "data": {
    "advisory_id": 51,
    "care_plan_id": 25,
    "patient_id": 10,
    "advisory_type": "measurement",
    "deleted": true
  },
  "message": "Draft advisory deleted",
  "error": null
}
```

Published advisories return `400` with `Published advisories are read-only`.

## 8. Search approved clinical terms

### Request

```http
GET /terminology/provider-terms?query=temp
X-Session-Token: <provider-session>
```

Optional tag filter:

```http
GET /terminology/provider-terms?query=temp&tag=measurement
```

### Query table

| Query | Type | Required | Validation |
| --- | --- | --- | --- |
| `query` | string | Yes | 3 to 80 characters. |
| `tag` | string | No | `medication`, `measurement`, `recommendation`, or `investigation`. |
| `limit` | integer | No | 1 to 20; default 20. |

### Success response

```json
{
  "success": true,
  "data": {
    "terms": [
      {
        "conceptId": "demo_term_temperature",
        "term": "Temperature",
        "tag": "measurement"
      }
    ],
    "query": "temp",
    "count": 1
  },
  "message": null,
  "error": null
}
```

Medication search returns only approved drug-catalog medicines. Legacy/demo non-catalog medicines are not returned for new medication authoring.

If the optional SVP terminology bundle is present, investigation search can also
return real SVP investigation terms such as `Complete blood count`. This fallback
does not broaden medication authoring; medicines still require the approved drug
catalogue.

Frontend should display `term` and friendly type label only. It should not show internal `conceptId` to normal users.

## 9. Get controls for selected term

Always call this before rendering type-specific fields.

### Request

```http
GET /terminology/provider-terms/{concept_id}/advisory-options
X-Session-Token: <provider-session>
```

Example:

```http
GET /terminology/provider-terms/2647801000189105/advisory-options
```

### Medication success response

```json
{
  "success": true,
  "data": {
    "term": {
      "conceptId": "2647801000189105",
      "term": "Levaz 500 mg oral tablet",
      "tag": "medication"
    },
    "options": {
      "frequencies": [
        { "value": "once_daily", "label": "Once daily" },
        { "value": "twice_daily", "label": "Twice daily" },
        { "value": "as_needed", "label": "As needed" }
      ],
      "duration_units": ["hours", "days", "weeks", "months"],
      "notifications": ["immediate", "daily_summary", "both", "none"],
      "instruction_suggestions": [
        "With or after meals",
        "Before meals",
        "After resting for five minutes",
        "Follow the provider's safety instructions"
      ],
      "dose_units": ["tablet"],
      "routes": ["oral"],
      "medication_details": {
        "generic": "Levofloxacin",
        "strength": "500 mg",
        "dose_form": "tablet",
        "route": "oral",
        "method": "oral",
        "supplier_name": "Sample supplier"
      }
    }
  },
  "message": null,
  "error": null
}
```

For catalog medicines, dose unit and route are server-derived. Frontend should show form/route/method/strength as read-only information and send back the exact allowed `dose_unit` and `route`.

### Measurement success response

```json
{
  "success": true,
  "data": {
    "term": {
      "conceptId": "demo_term_temperature",
      "term": "Temperature",
      "tag": "measurement"
    },
    "options": {
      "frequencies": [
        { "value": "once_daily", "label": "Once daily" }
      ],
      "duration_units": ["hours", "days", "weeks", "months"],
      "notifications": ["immediate", "daily_summary", "both", "none"],
      "instruction_suggestions": ["After resting for five minutes"],
      "measurement_units": ["°C", "°F"],
      "comparators": ["more_than", "less_than", "at_least", "at_most", "equal_to"]
    }
  },
  "message": null,
  "error": null
}
```

### Investigation success response

```json
{
  "success": true,
  "data": {
    "term": {
      "conceptId": "demo_term_hba1c",
      "term": "HbA1c",
      "tag": "investigation"
    },
    "options": {
      "frequencies": [
        { "value": "once_daily", "label": "Once daily" },
        { "value": "monthly", "label": "Monthly" }
      ],
      "duration_units": ["hours", "days", "weeks", "months"],
      "notifications": ["immediate", "daily_summary", "both", "none"],
      "instruction_suggestions": ["Follow the provider's safety instructions"],
      "priorities": ["routine", "urgent", "asap", "stat"]
    }
  },
  "message": null,
  "error": null
}
```

## 10. Add advisory to care plan

### Request

```http
POST /care-plans/{care_plan_id}/advisories
X-Session-Token: <provider-session>
Content-Type: application/json
```

### Common body shape

```json
{
  "concept_id": "demo_term_temperature",
  "term": "Temperature",
  "tag": "measurement",
  "configuration": {}
}
```

### Common field table

| Field | Type | Required | Validation |
| --- | --- | --- | --- |
| `concept_id` | string | Yes | 1 to 64 safe ID chars; must exist in approved terminology. |
| `term` | string | Yes | Must exactly match selected terminology term. |
| `tag` | string | Yes | Must exactly match selected term type. |
| `configuration` | object | Yes | Must match the selected type schema. Extra fields are rejected. |

The backend rechecks concept, term, and tag. A user cannot select Temperature but submit it as medicine.

## 11. Advisory configuration schemas

### 11.1 Common configuration fields

Every advisory type accepts these common fields:

| Field | Type | Required | Validation |
| --- | --- | --- | --- |
| `frequency` | string | Yes | `once_daily`, `twice_daily`, `three_times_daily`, `four_times_daily`, `every_4_hours`, `every_6_hours`, `weekly`, `monthly`, `as_needed`. |
| `duration_value` | integer | Yes | 1 to 365. |
| `duration_unit` | string | Yes | `hours`, `days`, `weeks`, `months`. |
| `additional_instructions` | string | No | Max 500 characters. |
| `non_response_warning` | object | No | For supported non-response alert configuration. |

`non_response_warning` shape:

```json
{
  "clinical_grace_minutes": 60,
  "notification": "immediate",
  "severity": "medium"
}
```

| Field | Type | Required | Validation |
| --- | --- | --- | --- |
| `clinical_grace_minutes` | integer | Yes | 1 to 1440. |
| `notification` | string | No | `immediate`, `daily_summary`, `both`, `none`; default `immediate`. |
| `severity` | string | No | `low`, `medium`, `high`, `critical`; default `medium`. |

### 11.2 Medication payload

Use when term `tag` is `medication`.

```json
{
  "concept_id": "2647801000189105",
  "term": "Levaz 500 mg oral tablet",
  "tag": "medication",
  "configuration": {
    "dose_value": 1,
    "dose_unit": "tablet",
    "route": "oral",
    "frequency": "once_daily",
    "duration_value": 3,
    "duration_unit": "days",
    "additional_instructions": "With or after meals"
  }
}
```

Medication-specific fields:

| Field | Type | Required | Validation |
| --- | --- | --- | --- |
| `dose_value` | number | Yes | Greater than 0, max 1,000,000. |
| `dose_unit` | string | Yes | Must be one of the dose units returned by advisory-options. For approved catalog medicines this is usually one exact value, for example `tablet`. |
| `route` | string | Yes | Must be one of the routes returned by advisory-options. For approved catalog medicines this is usually one exact value, for example `oral`. |

Medication safety:

- Only approved catalog medicines are accepted for new medication advisories.
- Backend checks patient allergy list against both the product term and generic ingredient.
- Allergy warning is blocking at publish time.

Sample success response:

```json
{
  "success": true,
  "data": {
    "id": 51,
    "advisory_type": "medication",
    "term": "Levaz 500 mg oral tablet",
    "tag": "medication",
    "configuration": {
      "frequency": "once_daily",
      "additional_instructions": "With or after meals",
      "duration_value": 3,
      "duration_unit": "days",
      "dose_value": 1,
      "dose_unit": "tablet",
      "route": "oral"
    },
    "allergy_warnings": [],
    "status": "DRAFT",
    "execution_status": "pending",
    "published_at": null,
    "created_at": "2026-06-23T09:05:00Z"
  },
  "message": "Advisory added",
  "error": null
}
```

Sample success response with allergy warning:

```json
{
  "success": true,
  "data": {
    "id": 52,
    "advisory_type": "medication",
    "term": "Levaz 500 mg oral tablet",
    "tag": "medication",
    "configuration": {
      "frequency": "once_daily",
      "duration_value": 3,
      "duration_unit": "days",
      "dose_value": 1,
      "dose_unit": "tablet",
      "route": "oral",
      "allergy_warnings": [
        {
          "code": "POTENTIAL_ALLERGY",
          "severity": "warning",
          "message": "Medication may conflict with recorded allergy Levofloxacin",
          "allergen": "Levofloxacin",
          "blocking": true
        }
      ]
    },
    "allergy_warnings": [
      {
        "code": "POTENTIAL_ALLERGY",
        "severity": "warning",
        "message": "Medication may conflict with recorded allergy Levofloxacin",
        "allergen": "Levofloxacin",
        "blocking": true
      }
    ],
    "status": "DRAFT",
    "execution_status": "pending",
    "published_at": null,
    "created_at": "2026-06-23T09:05:00Z"
  },
  "message": "Advisory added",
  "error": null
}
```

Frontend behavior for this warning: show red warning and do not let provider send until a safer medicine is chosen.

### 11.3 Measurement payload

Use when term `tag` is `measurement`.

```json
{
  "concept_id": "demo_term_temperature",
  "term": "Temperature",
  "tag": "measurement",
  "configuration": {
    "frequency": "four_times_daily",
    "duration_value": 5,
    "duration_unit": "days",
    "measurement_unit": "°F",
    "additional_instructions": "Record after resting for five minutes",
    "value_warning": {
      "condition": "more_than",
      "threshold_value": 100.4,
      "measurement_unit": "°F",
      "notification": "immediate",
      "severity": "critical"
    },
    "non_response_warning": {
      "clinical_grace_minutes": 60,
      "notification": "immediate"
    }
  }
}
```

Measurement-specific fields:

| Field | Type | Required | Validation |
| --- | --- | --- | --- |
| `measurement_unit` | string | Yes | Must be one of term-specific `measurement_units`. |
| `value_warning` | object | No | Creates provider alert if patient response crosses threshold. |

`value_warning` shape:

| Field | Type | Required | Validation |
| --- | --- | --- | --- |
| `condition` | string | Yes | `more_than`, `less_than`, `at_least`, `at_most`, `equal_to`. |
| `threshold_value` | number | Yes | -1,000,000 to 1,000,000. |
| `measurement_unit` | string | Yes | Must exactly equal parent `measurement_unit`. |
| `notification` | string | No | `immediate`, `daily_summary`, `both`, `none`. |
| `severity` | string | No | `low`, `medium`, `high`, `critical`. |

Backend rejects a warning unit mismatch, for example parent `°F` but warning `°C`.

### 11.4 Investigation payload

Use when term `tag` is `investigation`.

```json
{
  "concept_id": "demo_term_hba1c",
  "term": "HbA1c",
  "tag": "investigation",
  "configuration": {
    "priority": "urgent",
    "due_date": "2026-06-24",
    "upload_required": true,
    "alert_if_not_uploaded": true,
    "grace_period_value": 2,
    "grace_period_unit": "days",
    "frequency": "monthly",
    "duration_value": 3,
    "duration_unit": "months"
  }
}
```

Investigation-specific fields:

| Field | Type | Required | Validation |
| --- | --- | --- | --- |
| `priority` | string | Yes | `routine`, `urgent`, `asap`, `stat`. |
| `due_date` | date | Yes | Cannot be in the past; cannot be more than five years ahead. |
| `upload_required` | true | Yes | Must be exactly `true`. |
| `alert_if_not_uploaded` | boolean | No | Default `true`. |
| `grace_period_value` | integer | No | 0 to 30; default 2. |
| `grace_period_unit` | string | No | `hours` or `days`; default `days`. |

Do not send `attachment_required`. Backend expects `upload_required`.

### 11.5 Recommendation payload

Use when term `tag` is `recommendation`.

```json
{
  "concept_id": "demo_term_walking_exercise",
  "term": "Walking Exercise",
  "tag": "recommendation",
  "configuration": {
    "frequency": "once_daily",
    "duration_value": 4,
    "duration_unit": "weeks",
    "additional_instructions": "Walk for 20 minutes after breakfast",
    "non_response_warning": {
      "clinical_grace_minutes": 90,
      "notification": "daily_summary"
    }
  }
}
```

## 12. Publish/send care plan

There are two send modes.

| Mode | Endpoint | When to use |
| --- | --- | --- |
| Send all draft advisories in selected plan | `POST /care-plans/{care_plan_id}/publish` | Normal UI button: `Send care plan`. |
| Send one advisory | `POST /care-plans/{care_plan_id}/advisories/{advisory_id}/publish` | Useful for future per-card send. |

### Request

```json
{
  "confirmed": true
}
```

No other fields are accepted.

### What backend does during publish

1. Confirms current user is provider.
2. Confirms provider owns this plan.
3. Confirms provider still has ACTIVE relationship with patient.
4. Confirms at least one draft advisory exists.
5. Blocks publishing any allergy-conflict medication.
6. Marks plan `ACTIVE`.
7. Marks advisory `PUBLISHED` and immutable.
8. Generates scheduled patient tasks.
9. Creates and dispatches PostOffice events:
   - `schedule.generate`
   - `advisory.publish`
   - `task.generate`
10. Writes audit entries.

### Single-advisory publish response

```json
{
  "success": true,
  "data": {
    "advisory": {
      "id": 51,
      "advisory_type": "medication",
      "term": "Levaz 500 mg oral tablet",
      "tag": "medication",
      "configuration": {
        "frequency": "once_daily",
        "duration_value": 3,
        "duration_unit": "days",
        "dose_value": 1,
        "dose_unit": "tablet",
        "route": "oral"
      },
      "allergy_warnings": [],
      "status": "PUBLISHED",
      "execution_status": "pending",
      "published_at": "2026-06-23T09:10:00Z",
      "created_at": "2026-06-23T09:05:00Z"
    },
    "event_id": "evt_abc123",
    "acknowledgement": {
      "ack_id": "ack_xyz123",
      "event_id": "evt_abc123",
      "status": "received",
      "received_by": "rogi_mitra",
      "acknowledged_at": "2026-06-23T09:10:00Z"
    },
    "workflow": {
      "schedule": {
        "event_id": "evt_schedule",
        "acknowledgement": {}
      },
      "advisory": {
        "event_id": "evt_abc123",
        "acknowledgement": {}
      },
      "tasks": {
        "event_id": "evt_tasks",
        "acknowledgement": {}
      }
    }
  },
  "message": "Advisory published, routed, and acknowledged",
  "error": null
}
```

### Whole-plan publish response

```json
{
  "success": true,
  "data": {
    "id": 25,
    "patient": {
      "id": 10,
      "full_name": "Suraj Singh"
    },
    "provider_id": 2,
    "title": "Fever plan",
    "diagnosis": {
      "conceptId": "54150009",
      "term": "Upper Respiratory Tract Infection",
      "notes": "Cough and fever monitoring"
    },
    "status": "ACTIVE",
    "archived_at": null,
    "advisories": [
      {
        "id": 51,
        "advisory_type": "measurement",
        "term": "Temperature",
        "tag": "measurement",
        "configuration": {
          "frequency": "four_times_daily",
          "duration_value": 5,
          "duration_unit": "days",
          "measurement_unit": "°F"
        },
        "allergy_warnings": [],
        "status": "PUBLISHED",
        "execution_status": "pending",
        "published_at": "2026-06-23T09:10:00Z",
        "created_at": "2026-06-23T09:05:00Z"
      }
    ],
    "created_at": "2026-06-23T09:00:00Z",
    "updated_at": "2026-06-23T09:10:00Z",
    "event_id": "evt_abc123",
    "event_ids": ["evt_abc123"],
    "deliveries": [
      {
        "event_id": "evt_abc123",
        "acknowledgement": {},
        "workflow": {
          "schedule": {},
          "advisory": {},
          "tasks": {}
        }
      }
    ]
  },
  "message": "Care plan published",
  "error": null
}
```

### Allergy-blocked publish response

```json
{
  "success": false,
  "data": null,
  "message": null,
  "error": {
    "code": "BAD_REQUEST",
    "message": "Publishing blocked: Levaz 500 mg oral tablet conflicts with recorded allergy Levofloxacin",
    "details": null,
    "request_id": "..."
  }
}
```

Backend also creates a critical `allergy_conflict` alert and `alert.trigger` event. No tasks are generated for unsafe medication.

## 13. Patient views published advisories

```http
GET /me/advisories
X-Session-Token: <patient-session>
```

Sample response:

```json
{
  "success": true,
  "data": {
    "advisories": [
      {
        "id": 51,
        "advisory_type": "measurement",
        "advisory": "Temperature",
        "instruction": "Record Temperature in °F (four times daily) for 5 days. Record after resting for five minutes",
        "status": "PUBLISHED",
        "execution_status": "pending",
        "created_at": "2026-06-23T09:05:00Z",
        "published_at": "2026-06-23T09:10:00Z",
        "care_plan": {
          "id": 25,
          "title": "Fever plan",
          "status": "ACTIVE"
        }
      }
    ]
  },
  "message": null,
  "error": null
}
```

This endpoint is patient-only and returns simple patient-facing instructions.

## 14. Patient tasks generated from advisories

Publication generates tasks from frequency and duration for medication, measurement, and recommendation advisories. Investigation advisories create one report-upload task due on the configured due date.

| Advisory type | Patient task title | Expected response |
| --- | --- | --- |
| Medication | `Take <medicine> — <dose>, <route>` | `taken_or_missed` |
| Measurement | `Record <measurement> (<unit>)` | `numeric_value` |
| Investigation | `Upload <investigation> report` | `report_upload` |
| Recommendation | `<recommendation term>` | `done_or_missed` |

Schedule rules:

| Frequency | Interval |
| --- | --- |
| `once_daily` | 24 hours |
| `twice_daily` | 12 hours |
| `three_times_daily` | 8 hours |
| `four_times_daily` | 6 hours |
| `every_4_hours` | 4 hours |
| `every_6_hours` | 6 hours |
| `weekly` | 168 hours |
| `monthly` | 720 hours |
| `as_needed` | 1 task |

Task generation is capped at 500 tasks per advisory.

Investigation tasks use the configured `due_date` and are scheduled at 17:00 UTC on that date.

### Patient gets own tasks

```http
GET /me/tasks
X-Session-Token: <patient-session>
```

Optional:

```http
GET /me/tasks?execution_status=pending
```

Allowed execution status filters: `pending`, `completed`, `completed_late`, `missed`.

Sample response:

```json
{
  "success": true,
  "data": {
    "tasks": [
      {
        "task_id": "task_123abc",
        "advisory_id": 51,
        "care_plan_id": 25,
        "task_type": "measurement",
        "patient": {
          "id": 10,
          "full_name": "Suraj Singh"
        },
        "title": "Record Temperature (°F)",
        "advisory": "Temperature",
        "configuration": {
          "frequency": "four_times_daily",
          "duration_value": 5,
          "duration_unit": "days",
          "measurement_unit": "°F"
        },
        "expected_response": "numeric_value",
        "due_at": "2026-06-23T09:10:00Z",
        "grace_expires_at": "2026-06-23T10:10:00Z",
        "execution_status": "pending",
        "response": null,
        "created_at": "2026-06-23T09:10:00Z"
      }
    ]
  },
  "message": null,
  "error": null
}
```

### Provider gets linked patient tasks

```http
GET /provider/tasks
X-Session-Token: <provider-session>
```

Optional:

```http
GET /provider/tasks?patient_id=10&execution_status=pending
```

Only ACTIVE relationship tasks are returned.

## 15. Patient responds to tasks

### Request

```http
POST /tasks/{task_uid}/responses
X-Session-Token: <patient-session>
Content-Type: application/json
```

### Medication taken

```json
{
  "response_status": "taken"
}
```

### Medication missed

Medication missed requires a coded reason from `GET /terminology/response-reasons`.

```json
{
  "response_status": "missed",
  "reason": {
    "concept_id": "422587007",
    "term": "Nausea"
  }
}
```

### Measurement recorded

```json
{
  "response_status": "recorded",
  "numeric_value": 101,
  "measurement_unit": "°F"
}
```

The response unit must match the advisory unit.

### Recommendation done

```json
{
  "response_status": "done"
}
```

### Recommendation missed

```json
{
  "response_status": "missed"
}
```

### Response field table

| Field | Type | Required | Validation |
| --- | --- | --- | --- |
| `response_status` | string | Yes | Medication: `taken`/`missed`; measurement: `recorded`; recommendation: `done`/`missed`; investigation response uses upload endpoint. |
| `reason` | object | Only medication missed | Must exactly match approved response reason. |
| `numeric_value` | number | Measurement only | -1,000,000 to 1,000,000. |
| `measurement_unit` | string | Measurement only | Must match advisory unit. |

Response success:

```json
{
  "success": true,
  "data": {
    "task": {
      "task_id": "task_123abc",
      "execution_status": "completed",
      "response": {
        "response_id": "resp_123abc",
        "response_status": "recorded",
        "value": {
          "reason": null,
          "numeric_value": 101,
          "measurement_unit": "°F"
        },
        "is_late": false,
        "responded_at": "2026-06-23T09:30:00Z",
        "event_id": "evt_response",
        "attachment": null
      }
    },
    "response": {
      "response_id": "resp_123abc",
      "response_status": "recorded",
      "value": {
        "reason": null,
        "numeric_value": 101,
        "measurement_unit": "°F"
      },
      "is_late": false,
      "responded_at": "2026-06-23T09:30:00Z",
      "event_id": "evt_response",
      "attachment": null
    },
    "deliveries": [
      {
        "event_id": "evt_response",
        "acknowledgement": {}
      }
    ]
  },
  "message": "Response saved",
  "error": null
}
```

If measurement crosses configured `value_warning`, `deliveries` includes both `response.log` and `alert.trigger`, and provider sees a `value_threshold` alert.

Important backend rules:

- Only assigned patient may respond.
- Task must be pending.
- A task accepts exactly one successful response.
- Response is immutable after success.
- Numeric values are accepted only for measurement.
- Investigation uses upload endpoint, not JSON response.

## 16. Investigation report upload

### Request

```http
POST /tasks/{task_uid}/upload
X-Session-Token: <patient-session>
Content-Type: multipart/form-data
```

Form field:

| Field | Type | Required |
| --- | --- | --- |
| `file` | PDF or JPEG file | Yes |

Validation:

- Task must be an investigation task.
- Only assigned patient can upload.
- Only one upload/response is allowed.
- File must be PDF or JPEG.
- File MIME, extension, and file signature must match.
- Filename must be safe, 1 to 180 characters.
- File size must be within configured upload limit.
- Stored file gets random private name and SHA-256 hash.

Sample response:

```json
{
  "success": true,
  "data": {
    "task": {
      "task_id": "task_report",
      "execution_status": "completed",
      "response": {
        "response_id": "resp_report",
        "response_status": "uploaded",
        "value": {
          "attachment_id": "attachment_123abc"
        },
        "is_late": false,
        "responded_at": "2026-06-23T11:00:00Z",
        "event_id": "evt_upload",
        "attachment": {
          "attachment_id": "attachment_123abc",
          "filename": "HbA1c Report.pdf",
          "content_type": "application/pdf",
          "size_bytes": 36,
          "sha256": "abc123...",
          "uploaded_at": "2026-06-23T11:00:00Z"
        }
      }
    },
    "response": {
      "response_id": "resp_report",
      "response_status": "uploaded",
      "value": {
        "attachment_id": "attachment_123abc"
      },
      "is_late": false,
      "responded_at": "2026-06-23T11:00:00Z",
      "event_id": "evt_upload",
      "attachment": {
        "attachment_id": "attachment_123abc",
        "filename": "HbA1c Report.pdf",
        "content_type": "application/pdf",
        "size_bytes": 36,
        "sha256": "abc123...",
        "uploaded_at": "2026-06-23T11:00:00Z"
      }
    },
    "attachment": {
      "attachment_id": "attachment_123abc",
      "filename": "HbA1c Report.pdf",
      "content_type": "application/pdf",
      "size_bytes": 36,
      "sha256": "abc123...",
      "uploaded_at": "2026-06-23T11:00:00Z"
    },
    "delivery": {
      "event_id": "evt_upload",
      "acknowledgement": {}
    }
  },
  "message": "Report uploaded",
  "error": null
}
```

### Download report

```http
GET /attachments/{attachment_uid}
X-Session-Token: <patient-or-active-linked-provider-session>
```

Only the assigned patient or an ACTIVE linked provider can download. Response is the file stream with `X-Content-SHA256`.

## 17. Response reasons

Used when medication is missed.

```http
GET /terminology/response-reasons
X-Session-Token: <patient-session>
```

Optional:

```http
GET /terminology/response-reasons?query=nau
```

Sample response:

```json
{
  "success": true,
  "data": {
    "reasons": [
      {
        "conceptId": "422587007",
        "term": "Nausea",
        "tag": "response_reason"
      }
    ],
    "count": 1
  },
  "message": null,
  "error": null
}
```

Frontend sends the selected reason as:

```json
{
  "concept_id": "422587007",
  "term": "Nausea"
}
```

Backend checks the exact concept and term.

## 18. Provider alerts

### Get alerts

```http
GET /provider/alerts
X-Session-Token: <provider-session>
```

Optional:

```http
GET /provider/alerts?patient_id=10&alert_status=OPEN
```

Sample response:

```json
{
  "success": true,
  "data": {
    "alerts": [
      {
        "alert_id": "alert_123abc",
        "advisory_id": 51,
        "task_id": "task_123abc",
        "patient": {
          "id": 10,
          "full_name": "Suraj Singh"
        },
        "advisory": "Temperature",
        "alert_type": "value_threshold",
        "severity": "critical",
        "message": "Temperature value 101 °F crossed the configured threshold",
        "notification_mode": "immediate",
        "status": "OPEN",
        "event_id": "evt_alert",
        "acknowledged_at": null,
        "created_at": "2026-06-23T09:31:00Z"
      }
    ]
  },
  "message": null,
  "error": null
}
```

Alert types:

| Alert type | When created |
| --- | --- |
| `allergy_conflict` | Medication has blocking allergy conflict during publish. |
| `value_threshold` | Measurement response crosses configured threshold. |
| `non_response` | Task grace period expires and configured rule says alert should be created. |

### Acknowledge alert

```http
POST /provider/alerts/{alert_uid}/acknowledge
X-Session-Token: <provider-session>
Content-Type: application/json
```

```json
{
  "confirmed": true
}
```

Response:

```json
{
  "success": true,
  "data": {
    "alert_id": "alert_123abc",
    "status": "ACKNOWLEDGED",
    "changed": true
  },
  "message": "Alert acknowledged",
  "error": null
}
```

## 19. Evaluate overdue tasks

Provider can run overdue evaluation for all linked patients or one patient.

```http
POST /provider/tasks/evaluate-overdue
X-Session-Token: <provider-session>
Content-Type: application/json
```

All active linked patients:

```json
{
  "patient_id": null
}
```

One patient:

```json
{
  "patient_id": 10
}
```

Response:

```json
{
  "success": true,
  "data": {
    "evaluated": 1,
    "tasks": [],
    "alerts": [],
    "deliveries": []
  },
  "message": "Overdue tasks evaluated",
  "error": null
}
```

Backend behavior:

- Only provider may call.
- If `patient_id` is supplied, ACTIVE relationship is required.
- Only pending tasks past `grace_expires_at` are evaluated.
- Task becomes `missed`.
- Advisory execution status is aggregated.
- Configured non-response/investigation rules create alerts.
- Re-running does not duplicate completed/missed tasks.

## 20. Execution status rules

Execution status is server-owned. Frontend must never send it.

| Status | Meaning |
| --- | --- |
| `pending` | Task/advisory is waiting for patient action or generated tasks are still pending. |
| `completed` | All relevant tasks completed on time. |
| `completed_late` | At least one task completed after grace period and none are missed/pending. |
| `missed` | At least one task is missed and none are pending. |

Aggregation:

- If any task is pending, advisory stays `pending`.
- Else if any task is missed, advisory becomes `missed`.
- Else if any task is completed late, advisory becomes `completed_late`.
- Else advisory becomes `completed`.

## 21. Backend validation and security checklist

| Area | Backend protection |
| --- | --- |
| Role | Provider-only authoring; patient-only responses; provider-only alerts. |
| Session | All protected calls require valid `X-Session-Token`; raw token is hashed in storage. |
| Relationship | Create/publish/task views recheck ACTIVE consent-backed provider-patient relationship. |
| Ownership | Provider can edit/publish only own care plans. |
| Payload shape | Pydantic models reject undeclared fields. |
| Terminology | Concept ID, term, and tag must match approved terminology. |
| Medication catalog | New medication advisories accept only approved catalog concepts. |
| Medication safety | Allergy warnings are visible at add time and blocking at publish time. |
| Units/routes | Dose unit, route, and measurement unit must match advisory-options. |
| Date/range | Duration, grace, due date, numeric values, and thresholds have bounded ranges. |
| Duplicates | Same concept/type cannot be added twice to one care plan. |
| Publication | Published advisories are immutable and schedule cannot be generated twice. |
| Task count | Max 500 tasks per advisory. |
| Responses | Single-write immutable response per task. |
| Uploads | Private PDF/JPEG only, MIME/signature/extension/size checked, SHA-256 hash returned. |
| Events | PostOffice validates, sends, acknowledges, and stores event integrity. |
| Audit | Care plan create/update/archive, advisory create/publish, task response, upload, missed task, and alert actions are audited. |

## 22. Frontend must not add these fields

Do not send these from the Care Plan Builder:

| Do not send | Reason |
| --- | --- |
| `provider_id`, `provider_name` | Backend derives provider from session. |
| `status`, `Draft`, `PUBLISHED` | Backend controls state. |
| `execution_status` | Backend calculates from generated tasks/responses. |
| `created_at`, `updated_at`, `published_at` | Backend timestamps. |
| `allergy_warnings` | Backend calculates from patient allergy list. |
| `attachment_required` | Wrong field; investigation uses `upload_required: true`. |
| Medication `generic`, `strength`, `method`, `supplier_name` | Backend/catalog returns these as read-only info; frontend should not send them. |
| Unknown extra fields | Backend rejects with `422`. |

## 23. Minimum QA checklist

| Check | Expected result |
| --- | --- |
| Provider with ACTIVE patient relationship opens builder | Patient dropdown shows `name — mobile`; care-plan dropdown shows `plan — name — mobile`. |
| Provider without linked patients | Builder shows active relationship warning and create is disabled. |
| New care plan sends only `patient_id`, `title`, structured `diagnosis` | Backend returns `DRAFT` plan with `{term, notes, conceptId}` diagnosis; `conceptId` can be `null`. |
| Ready-to-send draft edit | Backend updates the draft advisory; audit has `advisory.updated`. |
| Ready-to-send draft delete | Backend deletes the draft advisory; audit has `advisory.deleted`. |
| Published advisory edit/delete | No UI buttons; direct API tampering returns `400 Published advisories are read-only`. |
| Search term under 3 characters | No API search or backend rejects. |
| Search medication not in catalog | No result / options rejected. |
| Tamper concept-term-tag mismatch | Backend returns `400`. |
| Send unknown config field | Backend returns `422`. |
| Medication wrong catalog dose unit | Backend returns `400`. |
| Measurement warning unit mismatch | Backend returns `400`. |
| Investigation past due date | Backend returns `400` or validation error. |
| Allergy medication added | Draft shows blocking warning. |
| Allergy medication publish | Backend blocks, creates `allergy_conflict`, no tasks generated. |
| Safe publish | Plan becomes `ACTIVE`, advisory becomes `PUBLISHED`, tasks/events generated. |
| Patient measurement wrong unit | Backend returns `400`. |
| Patient submits duplicate response | Backend returns `400`. |
| Fake PDF upload | Backend returns `400`. |
| Provider outside relationship downloads report | Backend returns `403`. |
| Overdue evaluation repeated | First call marks missed/alerts; second call evaluates 0. |

## 24. Simple frontend implementation order

1. On builder load, call linked patients and care plans together.
2. If no plans exist, open new-plan mode.
3. If plans exist, show existing plan selector and `New care plan`.
4. On new plan create, send linked patient, care-plan name, diagnosis term and optional notes, then reload plans and select the created plan.
5. In Add advice, search only after 3 characters.
6. After selecting a term, call advisory-options.
7. Render only fields for that type.
8. Before Add Advisory, do lightweight UI validation for friendly messages.
9. Send the exact type payload to `POST /care-plans/{id}/advisories`.
10. Reload plan list after add.
11. In Advisories section, show draft and published groups.
12. Draft `Ready to send` cards show Edit/Delete; published cards are read-only.
13. Disable send if draft advisory has blocking allergy warning.
14. On send, call publish with `{"confirmed": true}` only.

This keeps the UI simple for kids, older people, and non-technical users while keeping backend security strict.
