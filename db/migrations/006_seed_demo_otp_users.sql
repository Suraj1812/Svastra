PRAGMA foreign_keys = ON;

INSERT INTO users (
    user_id,
    name,
    username,
    mobile_number,
    email,
    password_hash,
    role,
    preferred_language,
    created_at,
    updated_at,
    is_active
) VALUES
    (
        'usr_demo_provider_001',
        'Demo Provider',
        'demo.provider',
        '+919900000001',
        'demo.provider@svastraplus.local',
        NULL,
        'PROVIDER',
        'en',
        '2026-06-15T00:00:00.000Z',
        '2026-06-15T00:00:00.000Z',
        1
    ),
    (
        'usr_demo_patient_001',
        'Demo Patient',
        'demo.patient',
        '+919900000002',
        'demo.patient@svastraplus.local',
        NULL,
        'PATIENT',
        'en',
        '2026-06-15T00:00:00.000Z',
        '2026-06-15T00:00:00.000Z',
        1
    ),
    (
        'usr_demo_caregiver_001',
        'Demo Caregiver',
        'demo.caregiver',
        '+919900000003',
        'demo.caregiver@svastraplus.local',
        NULL,
        'CAREGIVER',
        'en',
        '2026-06-15T00:00:00.000Z',
        '2026-06-15T00:00:00.000Z',
        1
    ),
    (
        'usr_demo_admin_001',
        'Demo Admin',
        'demo.admin',
        '+919900000004',
        'demo.admin@svastraplus.local',
        NULL,
        'ADMIN',
        'en',
        '2026-06-15T00:00:00.000Z',
        '2026-06-15T00:00:00.000Z',
        1
    )
ON CONFLICT(user_id) DO UPDATE SET
    name = excluded.name,
    username = excluded.username,
    mobile_number = excluded.mobile_number,
    email = excluded.email,
    password_hash = excluded.password_hash,
    role = excluded.role,
    preferred_language = excluded.preferred_language,
    updated_at = excluded.updated_at,
    is_active = excluded.is_active;
