# Week 4 Friday Transition Readiness Report

Date: 26 June 2026

Source reviewed:

- `SVASTRA+ MVP - WEEK 4 – FRIDAY ENGINEERING ACTIVITIES.md`

Theme: Demonstrator Closure, MVP Transition and Engineering Reset

## 1. Executive outcome

Week 4 Friday is a transition and consolidation day, not a feature-expansion
day. The demonstrator is now a validated behavioural reference for the MVP, but
it should not be treated as the final production architecture by default.

The repository currently proves the end-to-end care workflow:

```text
Identity and consent
  ↓
Provider-patient relationship
  ↓
Care plan creation
  ↓
Advisory authoring
  ↓
Schedule and task generation
  ↓
Patient response or upload
  ↓
Timeline and PostOffice event trace
  ↓
Provider task, alert and dashboard follow-up
```

For Week 5, the team should move from demonstrator-speed implementation to
disciplined vertical delivery:

```text
SQLite schema
  ↓
Repository layer
  ↓
Business service
  ↓
Clinical engine
  ↓
Backend API
  ↓
PostOffice integration
  ↓
Frontend API hook
  ↓
Frontend UI
  ↓
Integration test
  ↓
End-to-end demo
```

## 2. Friday objectives mapped to current repo state

| Friday objective | Current status | Notes |
| --- | --- | --- |
| Demonstrator closure | Ready | The current app validates the clinical workflow and integration story. |
| Frozen MVP scope discussion | Ready for product sign-off | The repo documents current API boundaries and known Week 5 transition notes. |
| Backend/frontend alignment | Ready | `api_contract.md` and the Care Plan Builder guide describe request/response payloads. |
| SQLite-first planning | Partially ready | Main app uses SQLite locally. Full production repository/migration separation remains a Week 5 architecture task. |
| SNOMED/SVP terminology readiness | Partially ready | SVP bundle is present and documented. Runtime uses a safe investigation-term fallback, not the full generated SQLite terminology DB yet. |
| PostOffice boundary | Ready | PostOffice is used as relay, acknowledgement and timeline infrastructure; clinical decisions remain in domain services/engines. |
| Engineering standards freeze | Ready for workshop | Validation, audit, immutable events, privacy redaction and strict payloads are documented. |
| Week 5 vertical method | Ready | This report and README state the required vertical delivery order. |

## 3. Backend demonstrator retrospective

### Reusable components

These parts are strong candidates for direct reuse or careful extraction during
Week 5:

- OTP/session flow with hashed raw session tokens.
- RBAC and consent-backed relationship checks.
- Care-plan/advisory service validation patterns.
- Advisory type-specific payload validation.
- Patient task response immutability.
- Private attachment validation and SHA-256 hashing.
- Alert lifecycle states: `NEW → ACKNOWLEDGED → RESOLVED`.
- PostOffice immutable event IDs, acknowledgements and retry controls.
- API Event Monitor privacy redaction and integrity digest model.

### Components that need production hardening or redesign

These demonstrator pieces should be reviewed before becoming production
baseline:

- Repository layer separation is still thin; services currently talk directly to
  SQLAlchemy models in many places.
- Clinical engines exist as service-level logic, but Week 5 should make engine
  boundaries explicit.
- Local SQLite compatibility helpers are useful for the demonstrator, but Week 5
  should formalize migration ownership and rollback planning.
- The SVP terminology integration currently reads the large JSON source for
  investigation fallback. The generated SQLite terminology store should become
  the production lookup path when Week 5 terminology work begins.
- The IDE drug-catalog sample is intentionally small. Full medication authoring
  needs the complete transformed drug catalog and tested crosswalks.

## 4. Frontend demonstrator retrospective

### Reusable patterns

- Simple patient/provider dashboard layout.
- Care Plan Builder sections: create/select plan, add advice, review/send.
- Patient task-first screens with short actions.
- Provider task and alert views.
- Timeline/Event Monitor visualization.
- Clear dropdown labels including patient mobile number where provider has an
  active relationship.

### Refinement needed for Week 5

- Extract a reusable component library instead of screen-local UI blocks.
- Keep forms short and non-technical.
- Keep concept IDs hidden from clinical users.
- Keep provider name, status and execution state server-derived.
- Make mobile responsiveness and accessibility checks part of each vertical
  feature, not a final cleanup task.

## 5. Diagnosis and terminology decisions frozen from this pass

Provider-facing care-plan diagnosis is not terminology-search driven in the
current UI. Providers enter:

- Linked Patient
- Care Plan Name
- Diagnosis
- Notes

They do not manually enter SNOMED or concept IDs.

Backend behaviour:

- `diagnosis.conceptId` is optional.
- New provider-entered diagnoses can return `"conceptId": null`.
- Existing stored/imported diagnosis concept IDs still return unchanged.
- Blank diagnosis concept IDs are normalized to `null`.
- Advisory terminology remains concept-driven and unchanged.

This split is intentional:

- Diagnosis text is a provider-facing care-plan context field.
- Advisory terms are actionable clinical instructions and therefore keep strict
  concept/term/tag validation.

## 6. SVP terminology readiness

The repository now includes the SVP terminology source bundle under
`svp_terminology_sqlitedb/`.

Tracked source files include:

- `svp_entry_terms.json`
- `svp_entry_terms_tags.tsv`
- `allergy_causative_pairs.json`
- `doseform_unitdose_mapping.json`
- `substance_ancestors.json`
- SQL build/query scripts
- bundle README and manifest

Current runtime integration:

- The app can read `svp_terminology_sqlitedb/svp_entry_terms.json`.
- `SVASTRA_TERMINOLOGY_ENTRY_TERMS_PATH` can point to another entry-term JSON.
- The fallback is exposed only for provider `investigation` term search.
- Example validated term: `Complete blood count` with concept ID `26604007`.
- Medication authoring is not broadened by the SVP entry-term fallback.

Reason for keeping medication restricted:

- The checked-in SVP folder does not include `ide_drug_catalog_transformed.json`.
- Medication dose, route, ingredient and allergy checks require drug-catalog
  metadata.
- The current app therefore keeps medication authoring limited to the approved
  drug-catalog sample.

Generated SQLite terminology database files are intentionally ignored by Git.
Engineers should rebuild them locally from `svp_terminology_sqlitedb/README.md`
when Week 5 SQLite terminology work starts.

## 7. PostOffice readiness boundary

PostOffice should remain a transport and traceability layer:

- validate canonical event shape;
- record immutable event history;
- relay events;
- record receiver acknowledgements;
- support retry/monitoring;
- expose redacted timeline/monitor views.

PostOffice should not decide:

- whether a medication is clinically safe;
- whether an advisory configuration is valid;
- whether a task is overdue;
- whether an alert should be created;
- whether a patient response is clinically acceptable.

Those remain domain/clinical-engine responsibilities.

## 8. Source-control and local artifact rules

The `.gitignore` has been expanded so future commits do not accidentally include:

- OS/editor noise;
- local environment files;
- Python caches and coverage files;
- frontend build outputs;
- local SQLite databases and journal files;
- private attachments;
- generated terminology SQLite databases.

The source SVP JSON/SQL documentation bundle remains tracked because the current
runtime fallback and Week 5 terminology planning depend on it.

## 9. Validation performed

Current validation set for this transition pass:

```text
pytest -q
npm run build
```

The backend tests include:

- care-plan creation without diagnosis concept ID;
- backward-compatible diagnosis with concept ID;
- blank concept ID normalization to null;
- advisory terminology safety unchanged;
- SVP investigation term search/options/advisory creation.

## 10. Week 5 go/no-go checklist

Before Week 5 feature development begins, the engineering team should explicitly
confirm:

- MVP scope is frozen.
- New features follow vertical implementation order.
- Repository/service/engine/API boundaries are agreed.
- SQLite migration ownership is clear.
- SVP terminology generated SQLite strategy is agreed.
- Full drug-catalog source and crosswalk gaps are understood.
- PostOffice remains non-clinical relay infrastructure.
- Frontend component library plan is accepted.
- API contracts are treated as the frontend/backend source of truth.

## 11. Final readiness judgement

The demonstrator phase is ready to close.

The repository is ready as a behavioural and contract baseline for Week 5.

The repository is not yet a finished production architecture baseline. Week 5
must convert the validated demonstrator behaviours into maintainable vertical
MVP implementation slices.
