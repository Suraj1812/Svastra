PRAGMA foreign_keys = ON;

ALTER TABLE timeline_events ADD COLUMN payload_sha256 VARCHAR(64);
ALTER TABLE timeline_events ADD COLUMN related_user_id INTEGER;
ALTER TABLE outbound_events ADD COLUMN last_error_code VARCHAR(64);
ALTER TABLE outbound_events ADD COLUMN last_error_message VARCHAR(255);
ALTER TABLE postoffice_acknowledgements ADD COLUMN retry_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE postoffice_acknowledgements ADD COLUMN last_attempt_at DATETIME;

CREATE INDEX IF NOT EXISTS idx_timeline_patient_occurred_id
    ON timeline_events(patient_id, occurred_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_timeline_patient_type_occurred
    ON timeline_events(patient_id, event_type, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_timeline_patient_related_occurred
    ON timeline_events(patient_id, related_user_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_outbound_patient_status_created
    ON outbound_events(patient_id, status, created_at DESC);

-- SQLite migrations cannot calculate SHA-256 without an extension. Application
-- startup safely backfills payload_sha256 for legacy rows before the monitor is used.
