# SVASTRA+ API Event Monitor — Operations and Security Guide

Version 1.0 — 19 June 2026

## Purpose

The API Event Monitor answers five operational questions without exposing more patient information than the signed-in role is allowed to see:

1. Was the healthcare event accepted into immutable history?
2. Where was it routed?
3. Is it queued, sent, failed, acknowledged, or missing transport state?
4. Was a receiver copy and acknowledgement recorded?
5. Does the stored event still match its integrity digest?

It is available in the Timeline tab for patients and currently consent-backed providers/caregivers. It is not a clinical task engine, alerting engine, scheduler, or substitute for production infrastructure monitoring.

## End-to-end flow

```text
Domain action
    ↓
Strict CEP validation (type, IDs, timestamp, source, payload, size)
    ↓
Actor, patient, consent and relationship authorization
    ↓
Immutable timeline row + SHA-256 digest + temporary queue row
    ↓
Bounded dispatch attempt
    ↓
Receiver copy + acknowledgement
    ↓
Temporary queue row removed; permanent history remains
    ↓
Role-scoped monitor summary, list and redacted detail
```

## Security controls

| Control | Implementation |
| --- | --- |
| Authentication | Every monitor request requires a valid `X-Session-Token`. Raw tokens are hashed in storage. |
| Authorization | Patient self-scope or ACTIVE consent-backed provider/caregiver relationship. Checked on every request. |
| Event-party isolation | Linked users see only events they authored or events that explicitly reference their user ID. |
| Enumeration resistance | Detail requires both patient scope and event ID; lookup is performed inside authorized patient scope. |
| Least disclosure | List pages return only a safe payload preview. Full detail is recursively redacted. |
| Caregiver privacy | Diagnosis, advisory body, clinical configuration and message text are redacted. |
| Integrity | Canonical CEP JSON is SHA-256 hashed when stored and checked when read. |
| Replay safety | Same queued ID + same canonical body is idempotent. Same ID + changed body is rejected. |
| Pagination safety | Cursor is HMAC-signed and bound to the active filter fingerprint. |
| Resource limits | 1 MiB API request ceiling, 64 KiB CEP payload ceiling, page maximum 100 and bounded time windows. |
| Delivery safety | Retry count is bounded by `POSTOFFICE_MAX_RETRIES` and retries are audited. |
| Browser/API safety | No-store caching, frame denial, MIME sniff protection, restrictive referrer and permissions policies. |
| Configuration safety | Startup rejects unsafe numeric bounds, wildcard/empty CORS origins, and cursor secrets shorter than 32 characters. |

## Monitor API map

| Endpoint | Use |
| --- | --- |
| `GET /postoffice/monitor/summary` | Health, counts, acknowledgement rate, latency and anomalies. |
| `GET /postoffice/monitor/events` | Newest-first filtered event stream with signed keyset pagination. |
| `GET /postoffice/monitor/events/{event_id}` | Lifecycle, integrity digest and role-redacted payload. |
| `POST /postoffice/events/{event_id}/retry` | Authorized bounded manual delivery retry. |

The full field contract and examples are in `api_contract.md`.

## Reading health

`healthy` means no matching event is failed, untracked, stale beyond five minutes, or integrity-mismatched. It does not mean every event is acknowledged: some event types intentionally remain `sent` until a receiver confirms them.

`attention` means at least one immediate condition exists:

- failed delivery;
- event without queue/ack state;
- SHA-256 mismatch;
- unacknowledged queue row older than five minutes.

## Incident checklist

### Failed delivery

1. Open event detail and record `event_id`, `last_error`, target and retry count.
2. Confirm the patient relationship is still ACTIVE.
3. Confirm retry count is below `POSTOFFICE_MAX_RETRIES`.
4. Fix the receiver problem before retrying.
5. Retry once and confirm the attempt count and last-attempt timestamp changed.

### Integrity mismatch

1. Do not retry or recreate the event under the same ID.
2. Record event ID, patient ID, request ID and expected digest.
3. Restrict database write access and preserve database/log snapshots.
4. Compare the canonical stored CEP with the originating domain/audit record.
5. Treat unexplained modification as a security incident.

### Untracked event

1. Check whether an acknowledgement and receiver copy were partially deleted.
2. Check database transaction and application logs around `recorded_at`.
3. Do not manufacture an acknowledgement manually.
4. Restore transport state only through an approved recovery procedure.

### Stale sent event

1. Check target application availability.
2. Check the receiver for an existing event copy before retrying.
3. Use the same immutable event ID; never create a second clinical event for a transport retry.

## Performance model

- List pages use composite patient/timestamp/type indexes.
- Pagination is keyset-based, so later pages do not pay increasing offset costs.
- Full payloads are loaded only for explicit detail requests.
- Page size is capped at 100; the UI uses 25.
- The frontend debounces event-ID prefix search and ignores stale responses.
- Summary and event page load in parallel.

## Configuration

| Environment variable | Default | Production guidance |
| --- | --- | --- |
| `POSTOFFICE_MAX_RETRIES` | `5` | Keep bounded; alert before raising. |
| `MONITOR_MAX_PAGE_SIZE` | `100` | Do not exceed 100 without load testing. |
| `MONITOR_MAX_WINDOW_DAYS` | `366` | Reduce for large tenants. |
| `MONITOR_CURSOR_SECRET` | local-only value | Replace with at least 32 random characters. |
| `MAX_REQUEST_BYTES` | `1048576` | Keep lower than reverse-proxy limit. |

The local mock OTP `123456` is for development only and must be replaced by a production OTP provider before deployment.
