-- Week 3 Friday v1.2: future-ready execution placeholder; no task engine yet.
ALTER TABLE advisories
ADD COLUMN execution_status VARCHAR(20) NOT NULL DEFAULT 'pending'
CHECK (execution_status IN ('pending', 'completed', 'completed_late', 'missed'));

CREATE INDEX IF NOT EXISTS idx_advisories_execution_status
ON advisories(execution_status);
