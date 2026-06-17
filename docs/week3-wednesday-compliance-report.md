# SVASTRA+ MVP Week 3 Wednesday Compliance Report

Date: 2026-06-17

Source reviewed:

- `/Users/surajsingh/Documents/svastraplus_mvp/SVASTRA+ MVP - Week 3 – Wednesday Engineering Activities.md`
- `/Users/surajsingh/Documents/svastra-auth-mvp/api_contract.md`

## Verification Summary

| Check | Result | Evidence |
| --- | --- | --- |
| Backend tests | Pass | `PYTHONPYCACHEPREFIX=/private/tmp/svastra-pycache ./venv/bin/pytest -q` -> 13 passed |
| Frontend production build | Pass | `npm run build` -> TypeScript and Vite build completed |
| Dependency audit | Pass | `npm audit --audit-level=high` -> 0 vulnerabilities |
| Browser consent flow | Pass | Seeded provider request -> Rogi login -> Pending Requests -> Details -> Alias edit -> Grant OTP -> ACTIVE -> Revoke OTP -> REVOKED |
| Responsive check | Pass | 390px, 820px, and 1440px viewports; no horizontal overflow |
| Console errors | Pass | Browser console error log empty during Consent Admin verification |

## Backend

| Wednesday Requirement | Status | Evidence |
| --- | --- | --- |
| Relationship consent persistence | Pass | `RelationshipConsent` model and `db/migrations/011_create_relationship_consents.sql` |
| `create_consent_request()` | Pass | Creates `PENDING` provider/caregiver access requests |
| `grant_consent()` | Pass | OTP-protected transition `PENDING -> ACTIVE` |
| `reject_consent()` | Pass | OTP-protected transition `PENDING -> REJECTED` |
| `revoke_consent()` | Pass | OTP-protected transition `ACTIVE -> REVOKED` |
| `get_active_consents()` | Pass | Returns `ACTIVE` consents |
| `get_pending_consents()` | Pass | Returns `PENDING` requests |
| `get_inactive_consents()` | Pass | Returns `REJECTED`, `REVOKED`, `EXPIRED` consents |
| Consent states | Pass | PENDING, ACTIVE, REJECTED, REVOKED, EXPIRED |
| Consent types | Pass | `provider_access`, `caregiver_access` |
| Access validation | Pass | `has_provider_access()`, `has_caregiver_access()`, `validate_access()` |
| Access rules | Pass | Only `ACTIVE` returns allowed; pending/rejected/revoked/expired denied |
| Consent OTP send/verify | Pass | `send_consent_otp()`, `verify_consent_otp()` and API endpoints |
| Consent audit trail | Pass | Audit actions `consent.request`, `consent.grant`, `consent.reject`, `consent.revoke` |
| CEP events | Pass | `ConsentCEPEvent` rows generated for `consent.request`, `consent.grant`, `consent.reject`, `consent.revoke` |

## APIs

| Endpoint | Status |
| --- | --- |
| `GET /consent/active` | Implemented |
| `GET /consent/pending` | Implemented |
| `GET /consent/inactive` | Implemented |
| `GET /consent/{id}` | Implemented |
| `POST /consent/request` | Implemented |
| `POST /consent/request/{id}/grant` | Implemented |
| `POST /consent/request/{id}/reject` | Implemented |
| `POST /consent/request/{id}/revoke` | Implemented |
| `POST /consent/send-otp` | Implemented |
| `POST /consent/verify-otp` | Implemented |
| `PUT /consent/{id}/alias` | Implemented |
| `api_contract.md` | Updated from Tuesday placeholders to Wednesday relationship consent contract |

## Frontend

| Wednesday Requirement | Status | Evidence |
| --- | --- | --- |
| Consent Admin menu within Rogi Mitra | Pass | Rogi dashboard tab renamed to `Consent Admin` |
| Active Consents screen | Pass | Alias, Role, Consent Type, Granted Date, Status, View Details, Edit Alias, Revoke |
| Pending Requests screen | Pass | Alias, Role, Consent Type, Request Date, Status, View Details, Grant, Reject, Edit Alias |
| Inactive Consents screen | Pass | Alias, Role, Consent Type, Decision Date, Status |
| Consent Details pop card | Pass | Registered Full Name, Patient Alias, Mobile Number, Role, Consent Type, Status, Relevant Dates |
| Mobile number only in details view | Pass | Browser verified list rows do not expose mobile number |
| Alias management | Pass | Create/default alias from registered name; edit alias max 60; no OTP |
| OTP grant flow | Pass | Send OTP -> Enter OTP -> Verify OTP -> Consent ACTIVE |
| OTP reject flow | Pass | API and tests cover rejected transition |
| OTP revoke flow | Pass | Confirm/action dialog -> Send OTP -> Enter OTP -> Verify OTP -> Consent REVOKED |

## Out-of-Scope Preserved

| Item | Status |
| --- | --- |
| Platform consent changes | Excluded; registration platform consent kept unchanged |
| Care plan/task/timeline/alert implementations | Excluded |
| PostOffice delivery worker | Excluded; CEP rows are generated for PostOffice consumption |
| Production OTP provider | Excluded; MVP mock OTP remains `123456` |

## Notes

- Wednesday changed relationship consent grant state from Tuesday placeholder `GRANTED` to authoritative `ACTIVE`; API contract and UI now use `ACTIVE`.
- The relationship consent API is real and persisted. Frontend request creation is not added to the provider dashboard because Wednesday frontend ownership focused on Rogi Consent Admin; provider request creation is available through `POST /consent/request`.
