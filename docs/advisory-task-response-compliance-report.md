# Advisory → Task → Response Compliance Report

Date: 22 June 2026

Sources: Week 2 Friday Engineering Exercise (Revised) and Advisory-to-Task-to-Response Workflow v1.0.

## Implemented workflow

```text
Advisory validated
→ schedule.generate
→ advisory.publish
→ task.generate
→ patient response or report upload
→ response.log
→ optional alert.trigger
→ task/advisory execution status update
→ mandatory audit history
```

## Requirement mapping

| Requirement | Status | Implementation |
| --- | --- | --- |
| Tag-driven controls | Complete | Server terminology metadata and dynamic provider form |
| Drug catalog dose form/route | Complete | Only catalogue medications are offered; form/route/method are read-only and server-enforced |
| Allergy safety | Complete | Blocking critical alert; no publication/task on conflict |
| Schedule generation | Complete | Frequency/duration engine with 500-task safety ceiling |
| Patient tasks | Complete | Medication, measurement, recommendation, investigation |
| Taken/Missed | Complete | Immutable medication response |
| Coded missed reason | Complete | Approved terminology only; no free text |
| Numeric measurement | Complete | Finite value and exact unit validation |
| Investigation report | Complete | Private PDF/JPEG upload and consent-scoped download |
| Response CEP | Complete | Stored state cross-checked before PostOffice acceptance |
| Threshold alert | Complete | Optional rule and notification preference |
| No-response alert | Complete | Grace evaluation, missed transition, no duplicates |
| Execution states | Complete | pending/completed/completed_late/missed on tasks and advisories |
| Audit log | Complete | Schedule, task, response, upload, alert and acknowledgement actions |
| Provider UI | Complete | Simple Tasks and Alerts views |
| Patient UI | Complete | Large, short Taken/Missed/Done/Save/Upload actions |
| Event Monitor | Complete | Full schedule→publish→task→response→alert lifecycle |

## Care Plan Builder document audit

The provider screen is intentionally short. Technical identifiers and routing settings remain enforced by the backend but are not shown to clinical users.

| Document requirement | Provider screen |
| --- | --- |
| Care Plan selection/creation | One searchable existing-plan selector plus `New care plan`. New-plan mode asks only for Patient and Care Plan Name. |
| Patient identity in plan selectors | New-plan patient and existing-plan search both show full name plus registered mobile number, returned only to the actively linked provider |
| Four advisory categories | Selected automatically from approved terminology metadata |
| Type-ahead after 3 characters | Implemented; concept ID remains hidden |
| Medication dose quantity | Large minus/value/plus control |
| Medication dose form, route, method | Trusted drug-catalog labels; not editable for catalog medicines |
| Frequency and duration | Approved searchable frequency combobox plus numeric duration and time unit |
| Additional medication instruction | Short autocomplete with approved suggestions; free text remains bounded to 500 characters |
| Measurement unit | Limited to units for the selected measurement |
| Measurement value rule | Comparator, threshold, unit and severity; optional |
| Measurement no-response rule | One checkbox and grace period; optional |
| Investigation due date and priority | Date picker plus Routine/Urgent/ASAP/Stat choice buttons |
| Investigation upload required | Visible and always on, matching the server rule |
| Investigation missing-report alert and grace | One checkbox plus 0–30 day stepper |
| Recommendation instruction | One short instruction field, frequency and duration |
| Allergy warning | Prominent and publication-blocking |
| Draft review and publish | One `Send care plan` action with confirmation; duplicate per-item send button removed |
| Published advisory view | Separate published list with advisory status, created date, execution status and published date |

Removed from the clinical form because it adds no user decision: a separate numbered `Choose a plan` section, permanently open create fields, repeated Provider and Draft boxes, editable catalog route/dose form, separate notification-routing dropdowns, and a second publish action. Week 4 uses structured diagnosis during new care-plan creation, but the provider enters only diagnosis term and notes. Diagnosis concept IDs are optional internal/imported identifiers and are never manually typed by the provider. Existing plan search and new-plan creation share one compact section. Provider ownership and Draft status remain mandatory server-derived fields.

## Verification

| Check | Result |
| --- | --- |
| Backend suite | 38 passed |
| Frontend TypeScript and production build | Passed |
| Patch whitespace validation | Passed |
