#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
if [ ! -f .env ]; then
  cp .env.example .env
  echo "已创建 .env。正式演示前请修改默认密码。"
fi
docker compose up --build -d
docker compose ps
echo "前端: http://localhost:8088"
echo "后端健康: http://localhost:8080/actuator/health"
