PRAGMA foreign_keys = ON;

ALTER TABLE care_plans ADD COLUMN is_archived BOOLEAN NOT NULL DEFAULT 0;
ALTER TABLE care_plans ADD COLUMN archived_at DATETIME;

CREATE TABLE IF NOT EXISTS patient_allergies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    allergen_term TEXT NOT NULL CHECK (length(trim(allergen_term)) BETWEEN 2 AND 160),
    status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'INACTIVE')),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE (patient_id, allergen_term)
);

CREATE INDEX IF NOT EXISTS idx_patient_allergies_patient_status
    ON patient_allergies(patient_id, status);
