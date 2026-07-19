ALTER TABLE idempotency_record ADD COLUMN lease_until TIMESTAMP WITH TIME ZONE;
ALTER TABLE idempotency_record ADD COLUMN source_call_id VARCHAR(36);
ALTER TABLE idempotency_record ADD COLUMN last_error_code VARCHAR(80);
ALTER TABLE idempotency_record ADD COLUMN recovery_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE idempotency_record ADD COLUMN version BIGINT NOT NULL DEFAULT 0;
CREATE INDEX idx_idempotency_state_lease ON idempotency_record(state, lease_until);

ALTER TABLE ai_call_log ADD COLUMN total_backoff_ms BIGINT NOT NULL DEFAULT 0;
ALTER TABLE ai_call_log ADD COLUMN http_status INTEGER;
ALTER TABLE ai_call_log ADD COLUMN replayed BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE ai_call_log ADD COLUMN parent_call_id VARCHAR(36);
ALTER TABLE ai_call_log ADD COLUMN started_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE ai_call_log ADD COLUMN completed_at TIMESTAMP WITH TIME ZONE;
UPDATE ai_call_log SET started_at = created_at WHERE started_at IS NULL;
ALTER TABLE ai_call_log ALTER COLUMN started_at SET NOT NULL;
CREATE INDEX idx_ai_call_status_time ON ai_call_log(status, created_at DESC);
CREATE INDEX idx_ai_call_parent ON ai_call_log(parent_call_id);

CREATE TABLE ai_call_attempt_log (
  id VARCHAR(36) PRIMARY KEY,
  call_id VARCHAR(36) NOT NULL REFERENCES ai_call_log(id) ON DELETE CASCADE,
  attempt_no INTEGER NOT NULL,
  status VARCHAR(30) NOT NULL,
  latency_ms BIGINT NOT NULL,
  http_status INTEGER,
  retryable BOOLEAN NOT NULL,
  backoff_ms BIGINT NOT NULL DEFAULT 0,
  error_code VARCHAR(80),
  error_message VARCHAR(500),
  started_at TIMESTAMP WITH TIME ZONE NOT NULL,
  completed_at TIMESTAMP WITH TIME ZONE NOT NULL,
  CONSTRAINT uq_ai_attempt_call_no UNIQUE(call_id, attempt_no)
);
CREATE INDEX idx_ai_attempt_call ON ai_call_attempt_log(call_id, attempt_no);

CREATE TABLE ai_rate_limit_bucket (
  id VARCHAR(36) PRIMARY KEY,
  scope VARCHAR(180) NOT NULL,
  window_start TIMESTAMP WITH TIME ZONE NOT NULL,
  request_count INTEGER NOT NULL,
  expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
  version BIGINT NOT NULL DEFAULT 0,
  CONSTRAINT uq_ai_rate_limit_scope_window UNIQUE(scope, window_start)
);
CREATE INDEX idx_ai_rate_limit_expiry ON ai_rate_limit_bucket(expires_at);
