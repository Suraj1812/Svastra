# SVASTRA+ Authentication MVP

End-to-end Week 3 Monday MVP implementation for authentication, OTP verification,
registration, session creation, role routing, and unified platform consent.

## Backend

```bash
./venv/bin/pip install -r requirements.txt
./venv/bin/uvicorn app.main:app --reload --port 8000
```

## Frontend

```bash
cd frontend
npm install
npm run generate:media
npm run dev
```

The frontend runs on `http://localhost:5173` and proxies API calls to
`http://localhost:8000`.

## Verification

```bash
PYTHONPYCACHEPREFIX=/private/tmp/svastra-pycache ./venv/bin/pytest -q
cd frontend && npm run build
```

## Demo Flow

1. `POST /auth/otp/send`
2. `POST /auth/otp/verify` with OTP `123456`
3. `POST /auth/register/provider`, `/auth/register/patient`, or `/auth/register/caregiver`
4. `POST /auth/session/validate`
5. `POST /auth/logout`

Patient registration requires `unified_consent_accepted: true`. When accepted,
the backend records the active consent version, timestamp, application name,
application version, and request IP address when available.

## Consent APIs

- `GET /consent/current`
- `POST /consent/patients/{patient_id}/accept`
- `GET /consent/patients/{patient_id}/status`
