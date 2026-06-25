PRAGMA foreign_keys = OFF;

CREATE TABLE IF NOT EXISTS clinical_alerts_new (
    id INTEGER NOT NULL,
    alert_uid VARCHAR(64) NOT NULL,
    advisory_id INTEGER NOT NULL,
    task_id INTEGER,
    provider_id INTEGER NOT NULL,
    patient_id INTEGER NOT NULL,
    alert_type VARCHAR(32) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    message VARCHAR(500) NOT NULL,
    notification_mode VARCHAR(32) NOT NULL DEFAULT 'immediate',
    status VARCHAR(20) NOT NULL DEFAULT 'NEW',
    event_id VARCHAR(64),
    acknowledged_at DATETIME,
    resolved_at DATETIME,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    CONSTRAINT ck_clinical_alerts_type CHECK (alert_type in ('allergy_conflict', 'non_response', 'value_threshold')),
    CONSTRAINT ck_clinical_alerts_severity CHECK (severity in ('low', 'medium', 'high', 'critical')),
    CONSTRAINT ck_clinical_alerts_status CHECK (status in ('NEW', 'ACKNOWLEDGED', 'RESOLVED')),
    CONSTRAINT ck_clinical_alerts_notification_mode CHECK (notification_mode in ('immediate', 'daily_summary', 'both')),
    FOREIGN KEY(advisory_id) REFERENCES advisories (id),
    FOREIGN KEY(task_id) REFERENCES care_tasks (id),
    FOREIGN KEY(provider_id) REFERENCES users (id),
    FOREIGN KEY(patient_id) REFERENCES users (id)
);

INSERT INTO clinical_alerts_new (
    id,
    alert_uid,
    advisory_id,
    task_id,
    provider_id,
    patient_id,
    alert_type,
    severity,
    message,
    notification_mode,
    status,
    event_id,
    acknowledged_at,
    resolved_at,
    created_at,
    updated_at
)
SELECT
    id,
    alert_uid,
    advisory_id,
    task_id,
    provider_id,
    patient_id,
    alert_type,
    severity,
    message,
    notification_mode,
    CASE status WHEN 'OPEN' THEN 'NEW' ELSE status END,
    event_id,
    acknowledged_at,
    NULL,
    created_at,
    COALESCE(created_at, CURRENT_TIMESTAMP)
FROM clinical_alerts;

DROP TABLE clinical_alerts;
ALTER TABLE clinical_alerts_new RENAME TO clinical_alerts;

CREATE UNIQUE INDEX IF NOT EXISTS ix_clinical_alerts_alert_uid ON clinical_alerts(alert_uid);
CREATE INDEX IF NOT EXISTS ix_clinical_alerts_advisory_id ON clinical_alerts(advisory_id);
CREATE INDEX IF NOT EXISTS ix_clinical_alerts_task_id ON clinical_alerts(task_id);
CREATE INDEX IF NOT EXISTS ix_clinical_alerts_provider_id ON clinical_alerts(provider_id);
CREATE INDEX IF NOT EXISTS ix_clinical_alerts_patient_id ON clinical_alerts(patient_id);
CREATE INDEX IF NOT EXISTS ix_clinical_alerts_alert_type ON clinical_alerts(alert_type);
CREATE INDEX IF NOT EXISTS ix_clinical_alerts_status ON clinical_alerts(status);
CREATE UNIQUE INDEX IF NOT EXISTS ix_clinical_alerts_event_id ON clinical_alerts(event_id);
CREATE INDEX IF NOT EXISTS idx_clinical_alerts_provider_status_created
  ON clinical_alerts(provider_id, status, created_at);

PRAGMA foreign_keys = ON;
