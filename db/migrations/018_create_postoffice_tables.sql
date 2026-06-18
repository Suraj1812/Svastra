PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS timeline_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL UNIQUE,
    event_type TEXT NOT NULL,
    patient_id INTEGER NOT NULL,
    actor_id TEXT NOT NULL,
    source_app TEXT NOT NULL,
    target_app TEXT NOT NULL,
    payload_json TEXT NOT NULL CHECK (json_valid(payload_json)),
    occurred_at DATETIME NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS outbound_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL UNIQUE,
    patient_id INTEGER NOT NULL,
    target_app TEXT NOT NULL,
    cep_json TEXT NOT NULL CHECK (json_valid(cep_json)),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'failed')),
    retry_count INTEGER NOT NULL DEFAULT 0 CHECK (retry_count >= 0),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_attempt_at DATETIME,
    acknowledged_at DATETIME,
    FOREIGN KEY (patient_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS postoffice_acknowledgements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ack_id TEXT NOT NULL UNIQUE,
    event_id TEXT NOT NULL UNIQUE,
    received_by TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status = 'received'),
    received_at DATETIME NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_timeline_patient_occurred
    ON timeline_events(patient_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_outbound_status_target_created
    ON outbound_events(status, target_app, created_at);
