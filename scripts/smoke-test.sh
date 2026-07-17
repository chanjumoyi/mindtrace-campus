#!/usr/bin/env sh
set -eu
BASE_URL="${BASE_URL:-http://localhost:8080/api/v1}"
USER_NAME="${SMOKE_USER:-student_demo}"
PASSWORD="${SMOKE_PASSWORD:-demo123}"

login_json=$(curl -fsS -H 'Content-Type: application/json' -d "{\"username\":\"$USER_NAME\",\"password\":\"$PASSWORD\"}" "$BASE_URL/auth/login")
token=$(printf '%s' "$login_json" | python3 -c 'import json,sys; print(json.load(sys.stdin)["data"]["accessToken"])')
auth="Authorization: Bearer $token"

curl -fsS -H "$auth" "$BASE_URL/me" >/dev/null
curl -fsS -H "$auth" "$BASE_URL/navigation" >/dev/null

task_json=$(curl -fsS -H "$auth" -H 'Content-Type: application/json' -d '{"moduleCode":"COMMON","taskType":"SMOKE_TEST","title":"C公共底座烟测"}' "$BASE_URL/tasks")
task_id=$(printf '%s' "$task_json" | python3 -c 'import json,sys; print(json.load(sys.stdin)["data"]["id"])')
curl -fsS -X PATCH -H "$auth" -H 'Content-Type: application/json' -d '{"status":"RUNNING","progress":50}' "$BASE_URL/tasks/$task_id/status" >/dev/null
curl -fsS -X PATCH -H "$auth" -H 'Content-Type: application/json' -d '{"status":"SUCCEEDED"}' "$BASE_URL/tasks/$task_id/status" >/dev/null

key="smoke-$(date +%s)-0000"
curl -fsS -H "$auth" -H 'Content-Type: application/json' -H "Idempotency-Key: $key" -d '{"moduleCode":"COMMON","operation":"echo","input":{"source":"smoke-test"}}' "$BASE_URL/ai/invoke" >/dev/null

echo "烟测通过：登录、个人资料、导航、任务状态机、AI网关。"
