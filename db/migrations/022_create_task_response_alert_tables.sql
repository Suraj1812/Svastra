PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS care_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_uid TEXT NOT NULL UNIQUE,
    advisory_id INTEGER NOT NULL,
    care_plan_id INTEGER NOT NULL,
    provider_id INTEGER NOT NULL,
    patient_id INTEGER NOT NULL,
    task_type TEXT NOT NULL CHECK (task_type IN ('medication','measurement','recommendation','investigation')),
    title TEXT NOT NULL,
    expected_response TEXT NOT NULL,
    ordinal INTEGER NOT NULL CHECK (ordinal > 0),
    due_at DATETIME NOT NULL,
    grace_expires_at DATETIME NOT NULL,
    execution_status TEXT NOT NULL DEFAULT 'pending' CHECK (execution_status IN ('pending','completed','completed_late','missed')),
    completed_at DATETIME,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (advisory_id) REFERENCES advisories(id) ON DELETE CASCADE,
    FOREIGN KEY (care_plan_id) REFERENCES care_plans(id),
    FOREIGN KEY (provider_id) REFERENCES users(id),
    FOREIGN KEY (patient_id) REFERENCES users(id),
    UNIQUE (advisory_id, ordinal)
);

CREATE INDEX IF NOT EXISTS idx_care_tasks_patient_status_due ON care_tasks(patient_id, execution_status, due_at);
CREATE INDEX IF NOT EXISTS idx_care_tasks_provider_status_due ON care_tasks(provider_id, execution_status, due_at);

CREATE TABLE IF NOT EXISTS task_responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    response_uid TEXT NOT NULL UNIQUE,
    task_id INTEGER NOT NULL UNIQUE,
    advisory_id INTEGER NOT NULL,
    patient_id INTEGER NOT NULL,
    response_status TEXT NOT NULL CHECK (response_status IN ('taken','missed','done','recorded','uploaded')),
    response_value_json TEXT NOT NULL CHECK (json_valid(response_value_json)),
    is_late BOOLEAN NOT NULL DEFAULT 0,
    response_event_id TEXT UNIQUE,
    responded_at DATETIME NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES care_tasks(id),
    FOREIGN KEY (advisory_id) REFERENCES advisories(id),
    FOREIGN KEY (patient_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS clinical_attachments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    attachment_uid TEXT NOT NULL UNIQUE,
    task_id INTEGER NOT NULL UNIQUE,
    response_id INTEGER UNIQUE,
    patient_id INTEGER NOT NULL,
    original_filename TEXT NOT NULL,
    content_type TEXT NOT NULL,
    size_bytes INTEGER NOT NULL CHECK (size_bytes > 0),
    sha256 TEXT NOT NULL,
    storage_path TEXT NOT NULL UNIQUE,
    uploaded_at DATETIME NOT NULL,
    FOREIGN KEY (task_id) REFERENCES care_tasks(id),
    FOREIGN KEY (response_id) REFERENCES task_responses(id),
    FOREIGN KEY (patient_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS clinical_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_uid TEXT NOT NULL UNIQUE,
    advisory_id INTEGER NOT NULL,
    task_id INTEGER,
    provider_id INTEGER NOT NULL,
    patient_id INTEGER NOT NULL,
    alert_type TEXT NOT NULL CHECK (alert_type IN ('allergy_conflict','non_response','value_threshold')),
    severity TEXT NOT NULL CHECK (severity IN ('low','medium','high','critical')),
    message TEXT NOT NULL,
    notification_mode TEXT NOT NULL DEFAULT 'immediate' CHECK (notification_mode IN ('immediate','daily_summary','both')),
    status TEXT NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN','ACKNOWLEDGED')),
    event_id TEXT UNIQUE,
    acknowledged_at DATETIME,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (advisory_id) REFERENCES advisories(id),
    FOREIGN KEY (task_id) REFERENCES care_tasks(id),
    FOREIGN KEY (provider_id) REFERENCES users(id),
    FOREIGN KEY (patient_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_clinical_alerts_provider_status_created ON clinical_alerts(provider_id, status, created_at);
