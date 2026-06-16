CREATE INDEX IF NOT EXISTS ix_users_role ON users (role);
CREATE INDEX IF NOT EXISTS ix_users_mobile_number ON users (mobile_number);

CREATE INDEX IF NOT EXISTS ix_sessions_user_id ON sessions (user_id);
CREATE INDEX IF NOT EXISTS ix_sessions_session_token ON sessions (session_token);
CREATE INDEX IF NOT EXISTS ix_sessions_expires_at ON sessions (expires_at);

CREATE INDEX IF NOT EXISTS ix_consent_acceptances_patient_id ON consent_acceptances (patient_id);
CREATE INDEX IF NOT EXISTS ix_consent_acceptances_consent_version
    ON consent_acceptances (consent_version);

CREATE INDEX IF NOT EXISTS ix_audit_logs_actor_user_id ON audit_logs (actor_user_id);
CREATE INDEX IF NOT EXISTS ix_audit_logs_action ON audit_logs (action);
CREATE INDEX IF NOT EXISTS ix_audit_logs_mobile_number ON audit_logs (mobile_number);
