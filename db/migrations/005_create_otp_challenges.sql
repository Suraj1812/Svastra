PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS otp_challenges (
    otp_id TEXT PRIMARY KEY,
    mobile_number TEXT NOT NULL COLLATE NOCASE CHECK (length(trim(mobile_number)) > 0),
    otp_hash TEXT NOT NULL CHECK (length(trim(otp_hash)) > 0),
    purpose TEXT NOT NULL CHECK (purpose IN ('registration', 'login')),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    expires_at TEXT NOT NULL,
    consumed_at TEXT,
    attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    max_attempts INTEGER NOT NULL DEFAULT 3 CHECK (max_attempts > 0),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'consumed', 'expired', 'blocked')),
    CHECK (attempt_count <= max_attempts),
    CHECK (consumed_at IS NULL OR status = 'consumed')
);

CREATE INDEX IF NOT EXISTS idx_otp_challenges_mobile_status
    ON otp_challenges (mobile_number, status);

CREATE INDEX IF NOT EXISTS idx_otp_challenges_expires_at
    ON otp_challenges (expires_at);

CREATE INDEX IF NOT EXISTS idx_otp_challenges_purpose_status
    ON otp_challenges (purpose, status);
