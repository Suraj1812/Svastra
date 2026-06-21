# SVASTRA+ Week 3 Friday Advisory Compliance Report

Date: 21 June 2026

Authoritative scope: Friday Engineering Activities v1.0 plus Additional Design v1.2.

## Outcome

The provider-to-patient advisory flow is implemented end to end. Week 3 execution state is stored and transported as `pending`. Task generation, scheduling, response capture, warning execution, alerts and daily summaries are intentionally not implemented because the authoritative Friday documents defer them.

## Requirement evidence

| Requirement | Result | Evidence |
| --- | --- | --- |
| Approved terminology search after three characters | Pass | Provider terminology API and debounced frontend search |
| Internal concept IDs hidden from clinical UI | Pass | Search results render only term and category |
| Server-resolved advisory category | Pass | Concept, exact term and tag are checked against terminology storage |
| Medication controls | Pass | Positive numeric dose, approved dose unit, route, frequency, duration and instructions |
| Drug catalog integration | Pass | Levaz and Loxof OZ are searchable; catalog metadata narrows tablet/oral controls |
| Measurement controls | Pass | Term-specific unit metadata and optional same-unit value warning |
| Investigation controls | Pass | Frequency, duration, instructions and priority; no forced Friday attachment |
| Recommendation controls | Pass | Selected recommendation term plus common controls; no duplicate forced instruction |
| Optional non-response configuration | Pass | Strict grace/notification settings stored only; no Week 3 engine |
| Allergy warning | Pass | Active allergy match is visible and non-blocking |
| Draft and immutable publication state | Pass | DRAFT → PUBLISHED only; repeat publication rejected |
| Execution placeholder | Pass | Database, provider API, patient API, CEP and monitor expose only `pending` |
| PostOffice delivery | Pass | Timeline → temporary outbound → receiver copy → acknowledgement → queue removal |
| API Event Monitor | Pass | Advisory event, delivery status, integrity, lifecycle and execution state visible |
| Auditability | Pass | Care-plan create/update/archive, advisory create/publish and monitor detail actions audited |
| Role and ownership security | Pass | Provider role, plan ownership and active consent-backed relationship rechecked |
| API documentation | Pass | `api_contract.md` documents every live operation and Friday payload table |

## Validation gates

- Backend schemas reject undeclared keys and invalid ranges.
- Measurement warning units must equal the selected measurement unit.
- Published CEP data must match the stored advisory identity and state.
- CEPs reject invalid IDs, naive/future timestamps, unsupported types, oversized payloads and modified duplicate IDs.
- Patient and provider data access stays relationship-scoped.
- The monitor applies role-based redaction and verifies stored payload SHA-256 digests.
