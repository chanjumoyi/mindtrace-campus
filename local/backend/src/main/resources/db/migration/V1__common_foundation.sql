CREATE TABLE sys_permission (
  id VARCHAR(36) PRIMARY KEY,
  code VARCHAR(100) NOT NULL UNIQUE,
  name VARCHAR(120) NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE TABLE sys_role (
  id VARCHAR(36) PRIMARY KEY,
  code VARCHAR(50) NOT NULL UNIQUE,
  name VARCHAR(120) NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE TABLE sys_role_permission (
  role_id VARCHAR(36) NOT NULL REFERENCES sys_role(id) ON DELETE CASCADE,
  permission_id VARCHAR(36) NOT NULL REFERENCES sys_permission(id) ON DELETE CASCADE,
  PRIMARY KEY (role_id, permission_id)
);

CREATE TABLE app_user (
  id VARCHAR(36) PRIMARY KEY,
  username VARCHAR(80) NOT NULL UNIQUE,
  password_hash VARCHAR(100) NOT NULL,
  display_name VARCHAR(100) NOT NULL,
  email VARCHAR(180),
  status VARCHAR(30) NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL,
  updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
  version BIGINT NOT NULL DEFAULT 0
);

CREATE TABLE app_user_role (
  user_id VARCHAR(36) NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  role_id VARCHAR(36) NOT NULL REFERENCES sys_role(id) ON DELETE CASCADE,
  PRIMARY KEY (user_id, role_id)
);

CREATE TABLE auth_session (
  id VARCHAR(36) PRIMARY KEY,
  user_id VARCHAR(36) NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  token_hash VARCHAR(64) NOT NULL UNIQUE,
  expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
  revoked_at TIMESTAMP WITH TIME ZONE,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL
);
CREATE INDEX idx_auth_session_user ON auth_session(user_id);
CREATE INDEX idx_auth_session_active ON auth_session(token_hash, expires_at);

CREATE TABLE common_task (
  id VARCHAR(36) PRIMARY KEY,
  owner_user_id VARCHAR(36) REFERENCES app_user(id),
  module_code VARCHAR(50) NOT NULL,
  task_type VARCHAR(80) NOT NULL,
  title VARCHAR(180) NOT NULL,
  status VARCHAR(30) NOT NULL,
  progress INTEGER NOT NULL DEFAULT 0,
  request_ref VARCHAR(200),
  result_ref VARCHAR(200),
  error_code VARCHAR(80),
  error_message VARCHAR(500),
  version BIGINT NOT NULL DEFAULT 0,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL,
  updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);
CREATE INDEX idx_common_task_owner ON common_task(owner_user_id, created_at DESC);
CREATE INDEX idx_common_task_module_status ON common_task(module_code, status);

CREATE TABLE file_object (
  id VARCHAR(36) PRIMARY KEY,
  owner_user_id VARCHAR(36) NOT NULL REFERENCES app_user(id),
  module_code VARCHAR(50) NOT NULL,
  original_name VARCHAR(255) NOT NULL,
  storage_name VARCHAR(255) NOT NULL UNIQUE,
  content_type VARCHAR(120) NOT NULL,
  size_bytes BIGINT NOT NULL,
  sha256 VARCHAR(64) NOT NULL,
  sensitivity_level VARCHAR(10) NOT NULL,
  metadata_json TEXT,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL,
  deleted_at TIMESTAMP WITH TIME ZONE
);
CREATE INDEX idx_file_owner ON file_object(owner_user_id, created_at DESC);
CREATE INDEX idx_file_module ON file_object(module_code, created_at DESC);

CREATE TABLE audit_log (
  id VARCHAR(36) PRIMARY KEY,
  actor_user_id VARCHAR(36),
  actor_username VARCHAR(80),
  action VARCHAR(120) NOT NULL,
  resource_type VARCHAR(80) NOT NULL,
  resource_id VARCHAR(100),
  result VARCHAR(30) NOT NULL,
  request_id VARCHAR(100),
  ip_address VARCHAR(80),
  detail_json TEXT,
  occurred_at TIMESTAMP WITH TIME ZONE NOT NULL
);
CREATE INDEX idx_audit_actor_time ON audit_log(actor_user_id, occurred_at DESC);
CREATE INDEX idx_audit_resource ON audit_log(resource_type, resource_id);
CREATE INDEX idx_audit_request ON audit_log(request_id);

CREATE TABLE idempotency_record (
  id VARCHAR(36) PRIMARY KEY,
  scope VARCHAR(80) NOT NULL,
  idempotency_key VARCHAR(120) NOT NULL,
  request_hash VARCHAR(64) NOT NULL,
  response_status INTEGER,
  response_body TEXT,
  state VARCHAR(20) NOT NULL,
  expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL,
  updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
  CONSTRAINT uq_idempotency_scope_key UNIQUE(scope, idempotency_key)
);
CREATE INDEX idx_idempotency_expiry ON idempotency_record(expires_at);

CREATE TABLE ai_call_log (
  id VARCHAR(36) PRIMARY KEY,
  actor_user_id VARCHAR(36),
  module_code VARCHAR(50) NOT NULL,
  operation VARCHAR(100) NOT NULL,
  provider_mode VARCHAR(40) NOT NULL,
  status VARCHAR(30) NOT NULL,
  attempts INTEGER NOT NULL,
  timeout_ms INTEGER NOT NULL,
  latency_ms BIGINT NOT NULL,
  request_id VARCHAR(100),
  idempotency_key VARCHAR(120),
  input_digest VARCHAR(64),
  output_digest VARCHAR(64),
  error_code VARCHAR(80),
  error_message VARCHAR(500),
  created_at TIMESTAMP WITH TIME ZONE NOT NULL
);
CREATE INDEX idx_ai_call_actor_time ON ai_call_log(actor_user_id, created_at DESC);
CREATE INDEX idx_ai_call_request ON ai_call_log(request_id);

CREATE TABLE module_registration (
  id VARCHAR(36) PRIMARY KEY,
  module_code VARCHAR(50) NOT NULL UNIQUE,
  module_name VARCHAR(120) NOT NULL,
  owner_code VARCHAR(10) NOT NULL,
  base_url VARCHAR(500),
  health_path VARCHAR(200),
  enabled BOOLEAN NOT NULL DEFAULT TRUE,
  status VARCHAR(30) NOT NULL,
  contract_version VARCHAR(30) NOT NULL,
  last_checked_at TIMESTAMP WITH TIME ZONE,
  updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);
