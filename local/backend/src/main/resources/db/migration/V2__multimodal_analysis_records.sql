CREATE TABLE multimodal_analysis_record (
  id VARCHAR(36) PRIMARY KEY,
  owner_user_id VARCHAR(36) NOT NULL REFERENCES app_user(id),
  module_type VARCHAR(30) NOT NULL,
  task_id VARCHAR(36) NOT NULL UNIQUE REFERENCES common_task(id) ON DELETE CASCADE,
  source_ref VARCHAR(200),
  title VARCHAR(180) NOT NULL,
  observation_json TEXT NOT NULL,
  ai_summary TEXT,
  provider VARCHAR(120),
  model VARCHAR(120),
  mock_result BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL,
  deleted_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_analysis_owner_time
  ON multimodal_analysis_record(owner_user_id, created_at DESC);
CREATE INDEX idx_analysis_module_time
  ON multimodal_analysis_record(module_type, created_at DESC);
