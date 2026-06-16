CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    role VARCHAR(32) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    mobile_number VARCHAR(32) NOT NULL UNIQUE,
    email_address VARCHAR(255),
    professional_category VARCHAR(100),
    registration_number VARCHAR(100),
    hpid_number VARCHAR(100),
    date_of_birth DATE,
    gender VARCHAR(64),
    preferred_language VARCHAR(64),
    abha_number VARCHAR(100),
    emergency_contact_name VARCHAR(255),
    emergency_contact_mobile VARCHAR(32),
    relationship_to_patient VARCHAR(100),
    terms_accepted BOOLEAN NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_users_role CHECK (role IN ('provider', 'patient', 'caregiver')),
    CONSTRAINT ck_users_terms_accepted CHECK (terms_accepted = 1),
    CONSTRAINT ck_provider_required_fields CHECK (
        role != 'provider'
        OR (professional_category IS NOT NULL AND registration_number IS NOT NULL)
    ),
    CONSTRAINT ck_patient_required_fields CHECK (
        role != 'patient'
        OR (date_of_birth IS NOT NULL AND gender IS NOT NULL AND preferred_language IS NOT NULL)
    ),
    CONSTRAINT ck_caregiver_required_fields CHECK (
        role != 'caregiver'
        OR (relationship_to_patient IS NOT NULL AND preferred_language IS NOT NULL)
    )
);

CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    session_token VARCHAR(255) NOT NULL UNIQUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS consent_acceptances (
    id INTEGER PRIMARY KEY,
    patient_id INTEGER NOT NULL,
    consent_version VARCHAR(100) NOT NULL,
    accepted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    application_name VARCHAR(100) NOT NULL,
    app_version VARCHAR(50) NOT NULL,
    ip_address VARCHAR(64),
    CONSTRAINT uq_patient_consent_version UNIQUE (patient_id, consent_version),
    FOREIGN KEY (patient_id) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY,
    actor_user_id INTEGER,
    actor_role VARCHAR(32),
    action VARCHAR(100) NOT NULL,
    mobile_number VARCHAR(32),
    ip_address VARCHAR(64),
    success BOOLEAN NOT NULL DEFAULT 1,
    metadata_json TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (actor_user_id) REFERENCES users (id)
);
