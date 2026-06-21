# SVASTRA+ Week 3 MVP Foundation

End-to-end identity, RBAC, patient-controlled consent, healthcare relationships,
PostOffice CEP delivery, API Event Monitor, care-plan authoring, advisory publication,
terminology, allergy warnings, and patient advisory display.

Friday v1.2 is implemented as a complete advisory path: the provider selects an
approved human-readable term, the server supplies and validates type-specific
controls, publication creates an immutable `advisory.publish` CEP with
`execution_status: pending`, PostOffice routes and acknowledges it, and both the
patient view and API Event Monitor display the pending execution state. Task
generation, scheduling, response capture and warning/alert engines remain later
phase work by design.

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
7. Provider publishes; PostOffice routes and acknowledges `advisory.publish`.
8. Patient opens My Advisories.
9. Patient or an actively linked provider/caregiver opens Timeline to inspect the
   role-scoped API Event Monitor, delivery lifecycle and integrity status.

Patient registration requires `unified_consent_accepted: true`. When accepted,
the backend records the active consent version, timestamp, application name,
application version, and request IP address when available.

Consent decisions use the already OTP-authenticated patient session plus a
confirmation body: `{"confirmed": true}`. No second OTP is requested.

## API Documentation

See [api_contract.md](./api_contract.md) for every endpoint, request/response
field, validation rule, role boundary, CEP route, and frontend integration flow.

See [docs/api-event-monitor-operations.md](./docs/api-event-monitor-operations.md)
for monitor architecture, privacy rules, filters, status interpretation,
performance controls and incident checks.

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
- Medication controls can be narrowed by the approved IDE drug-catalog metadata;
  internal concept identifiers are not rendered in clinical screens.
- API request bodies are capped at 1 MiB before request parsing.
- PostOffice retries are bounded and audited.
- Monitor pagination uses signed, filter-bound keyset cursors.
- Stored CEP documents carry SHA-256 integrity digests.
- Caregiver monitor payloads redact clinical instructions, diagnoses and messages.
- API responses include request IDs, processing time and restrictive security headers.
- Large JSON responses are compressed, while CORS accepts only explicit configured origins.
