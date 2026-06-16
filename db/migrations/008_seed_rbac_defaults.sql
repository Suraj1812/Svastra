PRAGMA foreign_keys = ON;

INSERT INTO roles (
    role_id,
    role_code,
    display_name,
    description,
    created_at,
    updated_at,
    is_active
) VALUES
    (
        'role_provider',
        'PROVIDER',
        'Provider',
        'Clinical user who manages patients, care plans, advisories, and longitudinal care workflows.',
        '2026-06-16T00:00:00.000Z',
        '2026-06-16T00:00:00.000Z',
        1
    ),
    (
        'role_patient',
        'PATIENT',
        'Patient',
        'Patient user who views their care timeline, consents, and assigned care tasks.',
        '2026-06-16T00:00:00.000Z',
        '2026-06-16T00:00:00.000Z',
        1
    ),
    (
        'role_caregiver',
        'CAREGIVER',
        'Caregiver',
        'Consent-linked caregiver user who supports patient task and alert visibility.',
        '2026-06-16T00:00:00.000Z',
        '2026-06-16T00:00:00.000Z',
        1
    ),
    (
        'role_admin',
        'ADMIN',
        'Admin',
        'Administrative user who manages platform configuration and consent operations.',
        '2026-06-16T00:00:00.000Z',
        '2026-06-16T00:00:00.000Z',
        1
    )
ON CONFLICT(role_id) DO UPDATE SET
    role_code = excluded.role_code,
    display_name = excluded.display_name,
    description = excluded.description,
    updated_at = excluded.updated_at,
    is_active = excluded.is_active;

INSERT INTO permissions (
    permission_id,
    permission_code,
    display_name,
    description,
    created_at,
    updated_at,
    is_active
) VALUES
    (
        'perm_view_provider_dashboard',
        'VIEW_PROVIDER_DASHBOARD',
        'View Provider Dashboard',
        'Open the provider care orchestration dashboard.',
        '2026-06-16T00:00:00.000Z',
        '2026-06-16T00:00:00.000Z',
        1
    ),
    (
        'perm_view_patient_dashboard',
        'VIEW_PATIENT_DASHBOARD',
        'View Patient Dashboard',
        'Open the patient care dashboard.',
        '2026-06-16T00:00:00.000Z',
        '2026-06-16T00:00:00.000Z',
        1
    ),
    (
        'perm_view_caregiver_dashboard',
        'VIEW_CAREGIVER_DASHBOARD',
        'View Caregiver Dashboard',
        'Open the caregiver care-support dashboard.',
        '2026-06-16T00:00:00.000Z',
        '2026-06-16T00:00:00.000Z',
        1
    ),
    (
        'perm_manage_consent',
        'MANAGE_CONSENT',
        'Manage Consent',
        'Create, view, and update consent records within the MVP consent model.',
        '2026-06-16T00:00:00.000Z',
        '2026-06-16T00:00:00.000Z',
        1
    ),
    (
        'perm_view_timeline',
        'VIEW_TIMELINE',
        'View Timeline',
        'View the patient longitudinal care timeline when consent allows.',
        '2026-06-16T00:00:00.000Z',
        '2026-06-16T00:00:00.000Z',
        1
    ),
    (
        'perm_create_care_plan',
        'CREATE_CARE_PLAN',
        'Create Care Plan',
        'Create and draft provider-led care plans.',
        '2026-06-16T00:00:00.000Z',
        '2026-06-16T00:00:00.000Z',
        1
    ),
    (
        'perm_respond_to_task',
        'RESPOND_TO_TASK',
        'Respond To Task',
        'Respond to assigned care tasks in a patient or caregiver workflow.',
        '2026-06-16T00:00:00.000Z',
        '2026-06-16T00:00:00.000Z',
        1
    )
ON CONFLICT(permission_id) DO UPDATE SET
    permission_code = excluded.permission_code,
    display_name = excluded.display_name,
    description = excluded.description,
    updated_at = excluded.updated_at,
    is_active = excluded.is_active;

INSERT INTO role_permissions (
    role_permission_id,
    role_id,
    permission_id,
    created_at
) VALUES
    ('rp_provider_view_provider_dashboard', 'role_provider', 'perm_view_provider_dashboard', '2026-06-16T00:00:00.000Z'),
    ('rp_provider_manage_consent', 'role_provider', 'perm_manage_consent', '2026-06-16T00:00:00.000Z'),
    ('rp_provider_view_timeline', 'role_provider', 'perm_view_timeline', '2026-06-16T00:00:00.000Z'),
    ('rp_provider_create_care_plan', 'role_provider', 'perm_create_care_plan', '2026-06-16T00:00:00.000Z'),
    ('rp_patient_view_patient_dashboard', 'role_patient', 'perm_view_patient_dashboard', '2026-06-16T00:00:00.000Z'),
    ('rp_patient_manage_consent', 'role_patient', 'perm_manage_consent', '2026-06-16T00:00:00.000Z'),
    ('rp_patient_view_timeline', 'role_patient', 'perm_view_timeline', '2026-06-16T00:00:00.000Z'),
    ('rp_patient_respond_to_task', 'role_patient', 'perm_respond_to_task', '2026-06-16T00:00:00.000Z'),
    ('rp_caregiver_view_caregiver_dashboard', 'role_caregiver', 'perm_view_caregiver_dashboard', '2026-06-16T00:00:00.000Z'),
    ('rp_caregiver_view_timeline', 'role_caregiver', 'perm_view_timeline', '2026-06-16T00:00:00.000Z'),
    ('rp_caregiver_respond_to_task', 'role_caregiver', 'perm_respond_to_task', '2026-06-16T00:00:00.000Z'),
    ('rp_admin_view_provider_dashboard', 'role_admin', 'perm_view_provider_dashboard', '2026-06-16T00:00:00.000Z'),
    ('rp_admin_view_patient_dashboard', 'role_admin', 'perm_view_patient_dashboard', '2026-06-16T00:00:00.000Z'),
    ('rp_admin_view_caregiver_dashboard', 'role_admin', 'perm_view_caregiver_dashboard', '2026-06-16T00:00:00.000Z'),
    ('rp_admin_manage_consent', 'role_admin', 'perm_manage_consent', '2026-06-16T00:00:00.000Z'),
    ('rp_admin_view_timeline', 'role_admin', 'perm_view_timeline', '2026-06-16T00:00:00.000Z'),
    ('rp_admin_create_care_plan', 'role_admin', 'perm_create_care_plan', '2026-06-16T00:00:00.000Z'),
    ('rp_admin_respond_to_task', 'role_admin', 'perm_respond_to_task', '2026-06-16T00:00:00.000Z')
ON CONFLICT(role_permission_id) DO UPDATE SET
    role_id = excluded.role_id,
    permission_id = excluded.permission_id;
