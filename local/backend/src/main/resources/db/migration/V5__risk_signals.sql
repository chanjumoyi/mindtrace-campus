CREATE TABLE risk_signals (
  id VARCHAR(36) PRIMARY KEY,
  user_id VARCHAR(36) NOT NULL REFERENCES app_user(id),
  level VARCHAR(10) NOT NULL CHECK (level IN ('RED', 'ORANGE', 'YELLOW', 'GREEN')),
  source VARCHAR(20) NOT NULL CHECK (source IN ('user_input', 'ai_output', 'mood_trend')),
  trigger_content TEXT NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE INDEX idx_risk_signals_user_time
  ON risk_signals(user_id, created_at DESC);
