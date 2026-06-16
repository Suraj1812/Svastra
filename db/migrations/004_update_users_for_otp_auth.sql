PRAGMA foreign_keys = OFF;

BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS users_otp_migration (
    user_id TEXT PRIMARY KEY,
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    username TEXT COLLATE NOCASE CHECK (username IS NULL OR length(trim(username)) > 0),
    mobile_number TEXT NOT NULL COLLATE NOCASE CHECK (length(trim(mobile_number)) > 0),
    email TEXT COLLATE NOCASE CHECK (email IS NULL OR length(trim(email)) > 0),
    password_hash TEXT CHECK (password_hash IS NULL OR length(trim(password_hash)) > 0),
    role TEXT NOT NULL CHECK (role IN ('PROVIDER', 'PATIENT', 'CAREGIVER', 'ADMIN')),
    preferred_language TEXT NOT NULL DEFAULT 'en' CHECK (length(trim(preferred_language)) > 0),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
);

INSERT INTO users_otp_migration (
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
)
SELECT
    user_id,
    name,
    username,
    CASE user_id
        WHEN 'usr_demo_provider_001' THEN '+919900000001'
        WHEN 'usr_demo_patient_001' THEN '+919900000002'
        WHEN 'usr_demo_caregiver_001' THEN '+919900000003'
        WHEN 'usr_demo_admin_001' THEN '+919900000004'
        ELSE '+910000' || printf('%06d', ROW_NUMBER() OVER (ORDER BY user_id))
    END AS mobile_number,
    email,
    NULL AS password_hash,
    CASE role
        WHEN 'Provider' THEN 'PROVIDER'
        WHEN 'Patient' THEN 'PATIENT'
        WHEN 'Caregiver' THEN 'CAREGIVER'
        WHEN 'Admin' THEN 'ADMIN'
        ELSE role
    END AS role,
    'en' AS preferred_language,
    created_at,
    strftime('%Y-%m-%dT%H:%M:%fZ', 'now') AS updated_at,
    is_active
FROM users
WHERE EXISTS (
    SELECT 1
    FROM sqlite_master
    WHERE type = 'table'
      AND name = 'users'
);

DROP TABLE IF EXISTS users;

ALTER TABLE users_otp_migration RENAME TO users;

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username
    ON users (username)
    WHERE username IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email
    ON users (email)
    WHERE email IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_mobile_number
    ON users (mobile_number);

COMMIT;

PRAGMA foreign_keys = ON;
