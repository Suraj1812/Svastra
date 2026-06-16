# SVASTRA+ MVP V3/V4 Compliance Report

Date: 2026-06-15

## Verification Summary

| Area | Result | Evidence |
| --- | --- | --- |
| Backend unit/integration tests | Pass | `./venv/bin/pytest -q` -> 6 passed |
| Frontend production build | Pass | `npm run build` -> Vite build completed |
| Dependency audit | Pass | `npm audit --audit-level=high` -> 0 vulnerabilities |
| Browser patient flow | Pass | Mobile -> OTP -> Patient Registration Form -> Unified Consent Display -> Dashboard |
| Browser provider flow | Pass | Mobile -> OTP -> Provider Registration Form -> Mantrana Dashboard |
| Browser caregiver flow | Pass | Mobile -> OTP -> Caregiver Registration Form -> Sahay Dashboard |
| Browser login flow | Pass | Mobile -> OTP -> Login -> role dashboard |
| Responsive layout | Pass | 390px, 820px, and 1440px viewports; no horizontal overflow |
| Media rendering | Pass | Real WebM clips and JPG posters load with readyState 4 |

## V3 Requirements

| Requirement | Status | Implementation Evidence |
| --- | --- | --- |
| End-to-end Registration -> OTP Verification -> Authentication -> Session Creation -> Role Recognition -> Dashboard Routing | Pass | `frontend/src/features/auth/hooks/useAuthWorkflow.ts`, `app/auth/auth_service.py`, browser flows |
| Authentication uses Mobile Number + OTP | Pass | `app/auth/otp_provider.py`, `frontend/src/features/auth/components/steps/MobileStep.tsx`, `OtpStep.tsx` |
| Passwords, Forgot Password, Password Reset, 2FA, Social Login deferred | Pass | No UI/API routes or text for these items; login browser check confirmed absent |
| `/db/migrations/001_create_core_tables.sql` available | Pass | `db/migrations/001_create_core_tables.sql` |
| `/db/migrations/002_create_indexes.sql` available | Pass | `db/migrations/002_create_indexes.sql` |
| `/db/migrations/003_seed_demo_users.sql` available | Pass | `db/migrations/003_seed_demo_users.sql` |
| Auth module includes `auth_service.py`, `session_manager.py`, `otp_provider.py` | Pass | `app/auth/` |
| `send_otp(mobile)` and `verify_otp(mobile, otp)` implemented | Pass | `app/auth/otp_provider.py` |
| Development OTP is `123456` | Pass | `app/auth/otp_provider.py`; tests/browser flows use `123456` |
| `register_provider`, `register_patient`, `register_caregiver` implemented | Pass | `app/auth/auth_service.py` |
| Registration allowed only after OTP verification | Pass | `_ensure_mobile_verified` in `app/auth/auth_service.py`; tests cover failure/success paths |
| `create_session`, `validate_session`, `destroy_session`, `logout` implemented | Pass | `app/auth/session_manager.py` |
| Provider required fields enforced | Pass | `app/schemas/registration.py`, `app/models/user.py`, provider form |
| Patient required fields enforced | Pass | `app/schemas/registration.py`, `app/models/user.py`, patient form |
| Caregiver required fields enforced | Pass | `app/schemas/registration.py`, `app/models/user.py`, caregiver form |
| Constrained occupation/gender/relationship/language values | Pass | `data/svp_entry_terms.json` uses authoritative `tag` + `term` entries; backend validators and frontend selects use those exact terms |
| Provider registration workflow | Pass | Browser verified |
| Patient registration workflow | Pass | Browser verified with V4 consent insertion |
| Caregiver registration workflow | Pass | Browser verified |
| Login workflow uses mobile + OTP only | Pass | Browser verified |
| Mantrana dashboard displays Patients, Care Plans, Timeline, Alerts, Profile | Pass | `frontend/src/shared/config/registrationOptions.ts`, browser verified |
| Rogi dashboard displays Tasks, Timeline, Messages, Profile | Pass | `frontend/src/shared/config/registrationOptions.ts`, browser verified |
| Sahay dashboard displays Patient Status, Timeline, Notifications, Profile | Pass | `frontend/src/shared/config/registrationOptions.ts`, browser verified |
| Provider routes to Mantrana dashboard | Pass | `/dashboards/mantrana`, browser/API tests |
| Patient routes to Rogi dashboard | Pass | `/dashboards/rogi`, browser/API tests |
| Caregiver routes to Sahay dashboard | Pass | `/dashboards/sahay`, browser/API tests |

## V4 Requirements

| Requirement | Status | Implementation Evidence |
| --- | --- | --- |
| Patient registration includes mandatory Platform Consent Acceptance | Pass | `ConsentStep.tsx`, `PatientRegistration.unified_consent_accepted` |
| Patient registration cannot complete without consent | Pass | Backend schema validation plus `auth_service.register_patient`; tests cover rejection |
| Consent document comes from `/data/svp_unified_consent.md` | Pass | Project consent markdown matches authoritative `svastraplus_mvp/data/svp_unified_consent.md`; served by `app/consent/consent_service.py` and `/consent/current` |
| `consent_service.py` created under consent module | Pass | `app/consent/consent_service.py` |
| `get_current_consent_version`, `record_consent_acceptance`, `get_patient_consent_status` implemented | Pass | `app/consent/consent_service.py` |
| Store patient_id, consent_version, accepted_at, application_name, app_version, optional IP | Pass | `app/models/consent.py`, API tests |
| Rogi flow includes Unified Consent Display -> Accept Consent -> Account Creation | Pass | `useAuthWorkflow.ts`, `ConsentStep.tsx`, browser verified |
| Consent screen shows Unified Consent Document | Pass | `ConsentStep.tsx`, browser verified |
| Consent checkbox text exactly present | Pass | `I have read and understood the consent` |
| Accept button text exactly present | Pass | `Accept & Continue` |
| Checkbox required before account creation | Pass | React Hook Form + Zod and backend schema validation |
| Platform Consent Acceptance and Consent Recording success criteria | Pass | API tests and browser patient flow |

## Out-of-Scope Exclusion Check

| Out-of-Scope Item | Status |
| --- | --- |
| Provider Access Consent | Excluded |
| Caregiver Access Consent | Excluded |
| Consent Revocation | Excluded |
| Consent Scope Management | Excluded |
| Patient Linkage | Excluded |
| Care Plans implementation | Excluded; dashboard shell label only |
| Advisory Builder | Excluded |
| Task Scheduler | Excluded |
| Tasks implementation | Excluded; dashboard shell label only |
| Timeline implementation | Excluded; dashboard shell label only |
| Alerts implementation | Excluded; dashboard shell label only |
| Drug Allergy Checks | Excluded |
| Critical Alert Rules | Excluded |
| Investigation Uploads | Excluded |
| PostOffice | Excluded |
| CEP | Excluded |

## Refactor Notes

- Frontend split into `features/auth`, `features/dashboard`, and `shared` modules.
- Backend route layer moved to `app/api/routes` with shared serialization in `app/api/serializers.py`.
- Old generated placeholder SVG/WebM assets removed from public media.
- Real optimized healthcare media is served from `frontend/public/media`.
