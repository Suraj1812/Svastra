PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS relationship_consents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    requestor_id INTEGER NOT NULL,
    requestor_role TEXT NOT NULL CHECK (length(trim(requestor_role)) > 0),
    consent_type TEXT NOT NULL CHECK (consent_type IN ('provider_access', 'caregiver_access')),
    alias TEXT NOT NULL CHECK (length(trim(alias)) > 0 AND length(alias) <= 60),
    status TEXT NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'ACTIVE', 'REJECTED', 'REVOKED', 'EXPIRED')),
    requested_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    granted_at DATETIME,
    rejected_at DATETIME,
    revoked_at DATETIME,
    expired_at DATETIME,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (requestor_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_relationship_consents_patient_status
    ON relationship_consents (patient_id, status);

CREATE INDEX IF NOT EXISTS idx_relationship_consents_requestor
    ON relationship_consents (requestor_id, consent_type, status);

CREATE INDEX IF NOT EXISTS idx_relationship_consents_patient_requestor
    ON relationship_consents (patient_id, requestor_id, consent_type);

CREATE TABLE IF NOT EXISTS consent_cep_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_name TEXT NOT NULL CHECK (event_name IN ('consent.request', 'consent.grant', 'consent.reject', 'consent.revoke')),
    consent_id INTEGER NOT NULL,
    payload_json TEXT NOT NULL CHECK (length(trim(payload_json)) > 0),
    published_at DATETIME,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (consent_id) REFERENCES relationship_consents(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_consent_cep_events_name_created
    ON consent_cep_events (event_name, created_at);

CREATE INDEX IF NOT EXISTS idx_consent_cep_events_consent
    ON consent_cep_events (consent_id);
