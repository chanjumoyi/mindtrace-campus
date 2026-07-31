CREATE TABLE action_plan (
  id VARCHAR(36) PRIMARY KEY,
  owner_user_id VARCHAR(36) NOT NULL REFERENCES app_user(id),
  title VARCHAR(120) NOT NULL,
  status VARCHAR(20) NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL,
  updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE TABLE action_plan_item (
  id VARCHAR(36) PRIMARY KEY,
  plan_id VARCHAR(36) NOT NULL REFERENCES action_plan(id) ON DELETE CASCADE,
  title VARCHAR(120) NOT NULL,
  scheduled_on DATE,
  status VARCHAR(20) NOT NULL,
  feedback VARCHAR(280),
  completed_at TIMESTAMP WITH TIME ZONE,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE INDEX idx_action_plan_owner_time
  ON action_plan(owner_user_id, updated_at DESC);
CREATE INDEX idx_action_plan_item_plan
  ON action_plan_item(plan_id, scheduled_on);
