PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS care_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider_id INTEGER NOT NULL,
    patient_id INTEGER NOT NULL,
    title TEXT NOT NULL CHECK (length(trim(title)) BETWEEN 3 AND 160),
    diagnosis TEXT CHECK (diagnosis IS NULL OR length(diagnosis) <= 255),
    status TEXT NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT', 'ACTIVE')),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (provider_id) REFERENCES users(id),
    FOREIGN KEY (patient_id) REFERENCES users(id),
    CHECK (provider_id <> patient_id)
);

CREATE TABLE IF NOT EXISTS advisories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    care_plan_id INTEGER NOT NULL,
    provider_id INTEGER NOT NULL,
    patient_id INTEGER NOT NULL,
    advisory_type TEXT NOT NULL CHECK (
        advisory_type IN ('medication', 'measurement', 'recommendation', 'investigation')
    ),
    concept_id TEXT NOT NULL CHECK (length(trim(concept_id)) > 0),
    term TEXT NOT NULL CHECK (length(trim(term)) > 0),
    tag TEXT NOT NULL CHECK (tag = advisory_type),
    configuration_json TEXT NOT NULL CHECK (json_valid(configuration_json)),
    status TEXT NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT', 'PUBLISHED')),
    published_at DATETIME,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (care_plan_id) REFERENCES care_plans(id) ON DELETE CASCADE,
    FOREIGN KEY (provider_id) REFERENCES users(id),
    FOREIGN KEY (patient_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_care_plans_provider_patient_status
    ON care_plans(provider_id, patient_id, status);
CREATE INDEX IF NOT EXISTS idx_advisories_care_plan_status
    ON advisories(care_plan_id, status);
CREATE UNIQUE INDEX IF NOT EXISTS idx_advisories_care_plan_concept_type
    ON advisories(care_plan_id, concept_id, advisory_type);
