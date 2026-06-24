ALTER TABLE timeline_events ADD COLUMN provider_id INTEGER;
ALTER TABLE timeline_events ADD COLUMN episode_id VARCHAR(100);
ALTER TABLE timeline_events ADD COLUMN encounter_id VARCHAR(100);

CREATE INDEX IF NOT EXISTS idx_timeline_patient_provider_occurred
  ON timeline_events(patient_id, provider_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_timeline_episode
  ON timeline_events(episode_id);
CREATE INDEX IF NOT EXISTS idx_timeline_encounter
  ON timeline_events(encounter_id);
