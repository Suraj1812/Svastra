PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS roles (
    role_id TEXT PRIMARY KEY,
    role_code TEXT NOT NULL COLLATE NOCASE CHECK (length(trim(role_code)) > 0),
    display_name TEXT NOT NULL CHECK (length(trim(display_name)) > 0),
    description TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    CHECK (role_code IN ('PROVIDER', 'PATIENT', 'CAREGIVER', 'ADMIN'))
);

CREATE TABLE IF NOT EXISTS permissions (
    permission_id TEXT PRIMARY KEY,
    permission_code TEXT NOT NULL COLLATE NOCASE CHECK (length(trim(permission_code)) > 0),
    display_name TEXT NOT NULL CHECK (length(trim(display_name)) > 0),
    description TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
);

CREATE TABLE IF NOT EXISTS role_permissions (
    role_permission_id TEXT PRIMARY KEY,
    role_id TEXT NOT NULL,
    permission_id TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    FOREIGN KEY (role_id) REFERENCES roles(role_id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES permissions(permission_id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_roles_role_code
    ON roles (role_code);

CREATE UNIQUE INDEX IF NOT EXISTS idx_permissions_permission_code
    ON permissions (permission_code);

CREATE UNIQUE INDEX IF NOT EXISTS idx_role_permissions_role_permission
    ON role_permissions (role_id, permission_id);

CREATE INDEX IF NOT EXISTS idx_role_permissions_permission_id
    ON role_permissions (permission_id);
