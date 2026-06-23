# SVASTRA+ Week 4 Monday/Tuesday Compliance Report

Date: 23 June 2026

Scope reviewed:

- `SVASTRA+ MVP - Week 4 – Monday Engineering Activities.md`
- `SVASTRA+ MVP - Week 4 – Tuesday Engineering Activities.md`

## Outcome

The connected provider → patient → provider care orchestration loop is implemented and validated.

Monday flow:

```text
Provider creates care plan with diagnosis
  ↓
Adds measurement / investigation / recommendation advisories
  ↓
Publishes care bundle
  ↓
PostOffice routes events
  ↓
Patient receives advisories and tasks
```

Tuesday flow:

```text
Patient receives tasks
  ↓
Submits measurement
  ↓
Uploads investigation PDF/JPEG
  ↓
Marks recommendation done/missed
  ↓
Provider sees returned task status and report
```

## Week 4 additions completed

| Requirement | Result | Evidence |
| --- | --- | --- |
| Diagnosis term, concept ID, notes | Done | `POST /care-plans` accepts structured `diagnosis: {conceptId, term, notes}` and returns it. |
| Diagnosis delivered to patient view | Done | `GET /me/advisories` includes diagnosis inside `care_plan`. |
| Diagnosis in publish payload | Done | `advisory.publish` CEP contains structured diagnosis and dispatcher verifies it against stored care-plan state. |
| Ready-to-send draft edit | Done | `PUT /care-plans/{care_plan_id}/advisories/{advisory_id}` updates DRAFT advisories only. |
| Ready-to-send draft delete | Done | `DELETE /care-plans/{care_plan_id}/advisories/{advisory_id}` deletes DRAFT advisories only. |
| Already sent read-only | Done | Published advisories show no edit/delete UI and backend rejects direct edit/delete with `400`. |
| Patient response capture | Done | `POST /tasks/{task_uid}/responses` stores immutable measurement/recommendation/medication responses. |
| Investigation upload | Done | `POST /tasks/{task_uid}/upload` stores private validated report attachments. |
| Provider receives updates | Done | `GET /provider/tasks` returns response state and attachment metadata for active linked patients. |

## Backend validation gates

- Provider authoring requires provider role and ACTIVE consent-backed relationship.
- Care-plan diagnosis object rejects invalid concept IDs, short terms, long terms, long notes and extra fields.
- Draft advisory edit reuses the same terminology, type-specific configuration, allergy and duplicate validations as create.
- Draft advisory delete checks provider ownership, non-archived plan state and DRAFT status.
- Published advisories are immutable for edit/delete.
- Publish rechecks active relationship and verifies CEP care-plan context, diagnosis, advisory identity and stored configuration.
- Patient responses are single-write and scoped to the assigned patient.
- Investigation uploads are private, size-limited, MIME/signature/extension checked and SHA-256 hashed.

## Frontend behavior

- New care-plan mode shows linked patient, care-plan name, diagnosis, SNOMED/concept ID and optional notes.
- Existing plan selector still shows `plan — patient — mobile`.
- `Ready to send` cards show Edit/Delete.
- `Published advisories` cards are read-only.
- Patient advisory cards display diagnosis context when present.

## Verification

| Check | Result |
| --- | --- |
| Care-plan backend regression suite | Passed |
| Full backend suite | Passed |
| Frontend production build | Passed |
| Whitespace/diff integrity check | Passed |

## Notes

Medication remains supported from the previous authorized advisory workflow, but the Week 4 Monday/Tuesday demonstration path can be completed entirely with measurement, investigation and recommendation advisories as requested by those documents.
