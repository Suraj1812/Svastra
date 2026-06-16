PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS consent_versions (
    consent_version TEXT PRIMARY KEY,
    title TEXT NOT NULL CHECK (length(trim(title)) > 0),
    markdown_file TEXT NOT NULL CHECK (length(trim(markdown_file)) > 0),
    effective_from TEXT NOT NULL,
    is_current INTEGER NOT NULL DEFAULT 0 CHECK (is_current IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_consent_versions_current
    ON consent_versions (is_current)
    WHERE is_current = 1;

CREATE TABLE IF NOT EXISTS platform_consents (
    consent_id TEXT PRIMARY KEY,
    patient_id TEXT NOT NULL,
    consent_version TEXT NOT NULL CHECK (length(trim(consent_version)) > 0),
    accepted_at TEXT NOT NULL,
    application_name TEXT NOT NULL CHECK (length(trim(application_name)) > 0),
    app_version TEXT NOT NULL CHECK (length(trim(app_version)) > 0),
    ip_address TEXT,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    FOREIGN KEY (patient_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (consent_version) REFERENCES consent_versions(consent_version)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_platform_consents_patient_current
    ON platform_consents (patient_id)
    WHERE is_active = 1;

CREATE INDEX IF NOT EXISTS idx_platform_consents_patient_id
    ON platform_consents (patient_id);

CREATE INDEX IF NOT EXISTS idx_platform_consents_consent_version
    ON platform_consents (consent_version);

CREATE INDEX IF NOT EXISTS idx_platform_consents_active
    ON platform_consents (is_active);
