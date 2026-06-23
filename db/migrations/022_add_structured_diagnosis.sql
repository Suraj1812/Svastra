PRAGMA foreign_keys = ON;

ALTER TABLE care_plans ADD COLUMN diagnosis_concept_id TEXT;
ALTER TABLE care_plans ADD COLUMN diagnosis_term TEXT;
ALTER TABLE care_plans ADD COLUMN diagnosis_notes TEXT;

CREATE INDEX IF NOT EXISTS idx_care_plans_diagnosis_concept
    ON care_plans(diagnosis_concept_id);
