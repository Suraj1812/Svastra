# SVASTRA+ Week 3 MVP Foundation

End-to-end identity, RBAC, patient-controlled consent, healthcare relationships,
PostOffice CEP delivery, care-plan authoring, advisory publication, terminology,
allergy warnings, and patient advisory display.

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

Patient registration requires `unified_consent_accepted: true`. When accepted,
the backend records the active consent version, timestamp, application name,
application version, and request IP address when available.

Consent decisions use the already OTP-authenticated patient session plus a
confirmation body: `{"confirmed": true}`. No second OTP is requested.

## API Documentation

See [api_contract.md](./api_contract.md) for every endpoint, request/response
field, validation rule, role boundary, CEP route, and frontend integration flow.

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
- `GET/POST/PUT/DELETE /care-plans/...`
- `POST /care-plans/{id}/advisories`
- `POST /care-plans/{id}/advisories/{advisory_id}/publish`
- `GET /me/advisories`
- `GET/POST /me/allergies`
- `POST /postoffice/send`
- `POST /postoffice/acknowledge`
