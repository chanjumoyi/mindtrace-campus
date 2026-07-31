CREATE TABLE mood_checkin (
  id VARCHAR(36) PRIMARY KEY,
  owner_user_id VARCHAR(36) NOT NULL REFERENCES app_user(id),
  mood SMALLINT NOT NULL CHECK (mood BETWEEN 1 AND 5),
  stress SMALLINT NOT NULL CHECK (stress BETWEEN 1 AND 5),
  sleep_hours NUMERIC(4,1) NOT NULL CHECK (sleep_hours BETWEEN 0 AND 24),
  tags_json TEXT NOT NULL,
  occurred_at TIMESTAMP WITH TIME ZONE NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE INDEX idx_mood_checkin_owner_time
  ON mood_checkin(owner_user_id, occurred_at DESC);
