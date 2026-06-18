PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS provider_patient_links (
    link_id TEXT PRIMARY KEY,
    provider_id INTEGER NOT NULL,
    patient_id INTEGER NOT NULL,
    source_consent_id INTEGER NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'ended')),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ended_at DATETIME,
    FOREIGN KEY (provider_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (patient_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (source_consent_id) REFERENCES relationship_consents(id),
    CHECK (provider_id <> patient_id),
    CHECK (ended_at IS NULL OR status = 'ended')
);

CREATE TABLE IF NOT EXISTS patient_caregiver_links (
    link_id TEXT PRIMARY KEY,
    patient_id INTEGER NOT NULL,
    caregiver_id INTEGER NOT NULL,
    source_consent_id INTEGER NOT NULL UNIQUE,
    relationship_type TEXT NOT NULL CHECK (length(trim(relationship_type)) > 0),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'ended')),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ended_at DATETIME,
    FOREIGN KEY (patient_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (caregiver_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (source_consent_id) REFERENCES relationship_consents(id),
    CHECK (patient_id <> caregiver_id),
    CHECK (ended_at IS NULL OR status = 'ended')
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_provider_patient_links_active
    ON provider_patient_links(provider_id, patient_id) WHERE status = 'active';
CREATE INDEX IF NOT EXISTS idx_provider_patient_links_patient_status
    ON provider_patient_links(patient_id, status);
CREATE UNIQUE INDEX IF NOT EXISTS idx_patient_caregiver_links_active
    ON patient_caregiver_links(patient_id, caregiver_id) WHERE status = 'active';
CREATE INDEX IF NOT EXISTS idx_patient_caregiver_links_caregiver_status
    ON patient_caregiver_links(caregiver_id, status);
