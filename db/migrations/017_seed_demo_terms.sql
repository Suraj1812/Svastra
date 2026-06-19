PRAGMA foreign_keys = ON;

INSERT INTO terms(concept_id, term, language) VALUES
    ('demo_term_paracetamol', 'Paracetamol', 'en'),
    ('demo_term_body_temperature', 'Body Temperature', 'en'),
    ('demo_term_blood_pressure', 'Blood Pressure', 'en'),
    ('demo_term_walking_exercise', 'Walking Exercise', 'en'),
    ('demo_term_dolo_650', 'Dolo 650 mg oral tablet', 'en'),
    ('demo_term_temperature', 'Temperature', 'en'),
    ('demo_term_exercise', 'Exercise', 'en'),
    ('demo_term_hba1c', 'HbA1c', 'en')
ON CONFLICT(concept_id) DO UPDATE SET
    term = excluded.term,
    language = excluded.language,
    updated_at = CURRENT_TIMESTAMP;

INSERT INTO term_tags(concept_id, tag) VALUES
    ('demo_term_paracetamol', 'medication'),
    ('demo_term_body_temperature', 'measurement'),
    ('demo_term_blood_pressure', 'measurement'),
    ('demo_term_walking_exercise', 'recommendation'),
    ('demo_term_dolo_650', 'medication'),
    ('demo_term_temperature', 'measurement'),
    ('demo_term_exercise', 'recommendation'),
    ('demo_term_hba1c', 'investigation')
ON CONFLICT(concept_id, tag) DO NOTHING;
