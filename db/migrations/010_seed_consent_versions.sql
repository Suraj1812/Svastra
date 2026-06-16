PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS consent_versions (
    consent_version TEXT PRIMARY KEY,
    title TEXT NOT NULL CHECK (length(trim(title)) > 0),
    markdown_file TEXT NOT NULL CHECK (length(trim(markdown_file)) > 0),
    effective_from TEXT NOT NULL,
    is_current INTEGER NOT NULL DEFAULT 0 CHECK (is_current IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_consent_versions_current
    ON consent_versions (is_current)
    WHERE is_current = 1;

INSERT INTO consent_versions (
    consent_version,
    title,
    markdown_file,
    effective_from,
    is_current,
    created_at,
    updated_at
) VALUES (
    'v1',
    'Svastra+ Unified Platform Consent',
    'consent_v1.md',
    '2026-06-16T00:00:00.000Z',
    1,
    '2026-06-16T00:00:00.000Z',
    '2026-06-16T00:00:00.000Z'
)
ON CONFLICT(consent_version) DO UPDATE SET
    title = excluded.title,
    markdown_file = excluded.markdown_file,
    effective_from = excluded.effective_from,
    is_current = excluded.is_current,
    updated_at = excluded.updated_at;
