# SVASTRA+ Demonstrator Foundation and MVP Transition Baseline

End-to-end identity, RBAC, patient-controlled consent, healthcare relationships,
PostOffice CEP delivery, API Event Monitor, care-plan authoring, advisory publication,
terminology, allergy warnings, and patient advisory display.

The complete terminology-driven care workflow is implemented: advisory creation,
bounded schedule generation, patient tasks, medication Taken/Missed responses,
coded missed reasons, measurement values, investigation uploads, response CEPs,
threshold/non-response/allergy alerts, execution-state aggregation, audit history,
PostOffice acknowledgements, provider views and the patient task UI.

## Week 4 Friday status

Week 4 Friday closes the demonstrator phase and prepares the project for
production-oriented MVP work. The current repository should be treated as a
validated behavioural baseline: useful for workflows, API contracts, terminology
readiness, UI learning and backend validation patterns. Week 5 implementation
should still follow disciplined vertical delivery: schema, repository, service,
engine, API, PostOffice integration, frontend hook, frontend screen and
end-to-end test.

See [docs/week4-friday-transition-readiness-report.md](./docs/week4-friday-transition-readiness-report.md)
for the demonstrator closure, MVP transition checklist, backend/frontend reuse
notes, SQLite/SVP terminology readiness, and the go/no-go summary.

## Backend

```bash
./venv/bin/pip install -r requirements.txt
./venv/bin/uvicorn app.main:app --reload --port 8000
```

## Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend runs on `http://localhost:5173` and proxies API calls to
`http://localhost:8000`.

## Verification

```bash
PYTHONPYCACHEPREFIX=/private/tmp/svastra-pycache ./venv/bin/pytest -q
cd frontend && npm run build
```

## End-to-End Demo Flow

1. `POST /auth/otp/send`
2. `POST /auth/otp/verify` with OTP `123456`
3. Register/login provider and patient.
4. Provider requests access; patient confirms consent.
5. Backend creates the consent-backed provider-patient relationship.
6. Provider creates a care plan and validated advisory.
7. Provider publishes; schedule and tasks are generated and all three workflow CEPs are acknowledged.
8. Patient opens Tasks and responds or uploads a report.
9. Backend records `response.log`, updates execution state, and creates `alert.trigger` only for breached rules.
10. Provider reviews Tasks and Alerts.
11. Patient or an actively linked provider/caregiver opens Timeline to inspect the
   role-scoped API Event Monitor, delivery lifecycle and integrity status.

Patient registration requires `unified_consent_accepted: true`. When accepted,
the backend records the active consent version, timestamp, application name,
application version, and request IP address when available.

Consent decisions use the already OTP-authenticated patient session plus a
confirmation body: `{"confirmed": true}`. No second OTP is requested.

## API Documentation

See [api_contract.md](./api_contract.md) for every endpoint, request/response
field, validation rule, role boundary, CEP route, and frontend integration flow.

See [docs/care-plan-builder-advisory-payload-guide.md](./docs/care-plan-builder-advisory-payload-guide.md)
for the practical Care Plan Builder handoff: screen behavior, situations,
payload examples, responses, validation rules, and QA checks.

See [docs/week4-monday-tuesday-compliance-report.md](./docs/week4-monday-tuesday-compliance-report.md)
for the Week 4 Monday/Tuesday orchestration completion report.

See [docs/week4-friday-transition-readiness-report.md](./docs/week4-friday-transition-readiness-report.md)
for the Friday engineering reset and Week 5 readiness report.

See [docs/api-event-monitor-operations.md](./docs/api-event-monitor-operations.md)
for monitor architecture, privacy rules, filters, status interpretation,
performance controls and incident checks.

## Terminology and diagnosis notes

- Provider-facing care-plan creation asks only for linked patient, care-plan
  name, diagnosis and notes. Providers never manually type SNOMED/concept IDs
  for diagnosis.
- Diagnosis `conceptId` is optional and may return as `null` for
  provider-entered diagnoses. Existing stored/imported diagnosis concept IDs
  continue to load and return unchanged.
- Advisory terminology is still concept-driven. The frontend displays readable
  terms only, while the API sends the selected `concept_id`, `term` and `tag`.
- The optional SVP terminology bundle in `svp_terminology_sqlitedb/` is used as
  a safe fallback for investigation terms only. Medication authoring remains
  restricted to the approved drug catalogue because dosing and allergy safety
  require catalogue metadata.
- The generated SQLite terminology database file is intentionally ignored by
  Git. Rebuild it locally from `svp_terminology_sqlitedb/README.md` when needed.

## Main API Areas

- `GET /consent/current`
- `GET /me/consent-status`
- `POST /consent/platform/accept`
- `GET /consent/active`
- `GET /consent/pending`
- `GET /consent/inactive`
- `GET /consent/requests`
- `GET /consent/{id}`
- `POST /consent/request`
- `POST /consent/request/{id}/grant`
- `POST /consent/request/{id}/reject`
- `POST /consent/request/{id}/revoke`
- `PUT /consent/{id}/alias`
- `GET /me/permissions`
- `GET/POST/DELETE /relationships/...`
- `GET /terminology/provider-terms`
- `GET /terminology/provider-terms/{concept_id}/advisory-options`
- `GET/POST/PUT/DELETE /care-plans/...`
- `POST /care-plans/{id}/advisories`
- `POST /care-plans/{id}/advisories/{advisory_id}/publish`
- `GET /me/tasks`
- `GET /provider/tasks`
- `POST /tasks/{task_uid}/responses`
- `POST /tasks/{task_uid}/upload`
- `GET /attachments/{attachment_uid}`
- `POST /provider/tasks/evaluate-overdue`
- `GET /provider/alerts`
- `POST /provider/alerts/{alert_uid}/acknowledge`
- `GET /me/advisories`
- `GET/POST /me/allergies`
- `POST /postoffice/send`
- `POST /postoffice/acknowledge`
- `GET /postoffice/monitor/summary`
- `GET /postoffice/monitor/events`
- `GET /postoffice/monitor/events/{event_id}`

## Backend Hardening

- Raw session tokens are stored only as SHA-256 hashes.
- CEP IDs and payloads are immutable; reusing an ID with different content is rejected.
- CEP payloads have strict event-specific validation and a 64 KiB ceiling.
- Advisory CEPs are cross-checked against stored plan ownership, active consent,
  published status, concept, term, type, and Week 3 execution state.
- New medication advisories accept only approved IDE drug-catalog concepts; dose form, route and administration method are server-derived;
  internal concept identifiers are not rendered in clinical screens.
- Task generation is capped at 500 per advisory.
- Medication-miss reasons must use exact approved coded terminology.
- Investigation files are private, size/MIME/signature checked, SHA-256 hashed,
  randomly named and consent-scoped on every download.
- Responses are single-write and immutable; task/advisory status is server-owned.
- API request bodies are capped at 1 MiB before request parsing.
- PostOffice retries are bounded and audited.
- Monitor pagination uses signed, filter-bound keyset cursors.
- Stored CEP documents carry SHA-256 integrity digests.
- Caregiver monitor payloads redact clinical instructions, diagnoses and messages.
- API responses include request IDs, processing time and restrictive security headers.
- Large JSON responses are compressed, while CORS accepts only explicit configured origins.
