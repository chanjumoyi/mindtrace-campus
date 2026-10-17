# 手写数据采集端部署包

本目录将 `frontend/handwriting-collector-mobile` 构建为只读 Nginx 容器，供服务器人员部署。当前版本是移动端网页应用：采集结果保存在用户设备并导出 JSON，尚未向服务器自动上传数据。

## 服务器要求

- Linux 服务器（推荐 Ubuntu 22.04/24.04）
- Docker Engine 24 或更高版本
- Docker Compose v2
- 一个已经解析到服务器的域名
- 服务器现有的 Nginx、Caddy 或其他 HTTPS 反向代理

## 首次部署

```bash
git clone <仓库地址> mindtrace-campus
cd mindtrace-campus
git switch codex/handwriting-collector-deploy
cp deploy/handwriting-collector/.env.example deploy/handwriting-collector/.env
docker compose --env-file deploy/handwriting-collector/.env \
  -f deploy/handwriting-collector/compose.yaml config
docker compose --env-file deploy/handwriting-collector/.env \
  -f deploy/handwriting-collector/compose.yaml up -d --build
curl --fail http://127.0.0.1:8081/healthz
```

健康检查返回 `ok` 后，应用可通过服务器本机的 `127.0.0.1:8081` 访问。默认不直接暴露到公网，必须由 HTTPS 反向代理提供外部访问。

## Nginx HTTPS 反向代理示例

证书可由服务器现有的 Certbot 或运维平台管理。把下面的域名和证书路径替换为真实配置：

```nginx
server {
    listen 443 ssl http2;
    server_name collector.example.edu.cn;

    ssl_certificate /etc/letsencrypt/live/collector.example.edu.cn/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/collector.example.edu.cn/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8081;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

数位笔事件和笔压依赖浏览器 Pointer Events。正式环境必须使用 HTTPS；不要用公网 HTTP 地址进行采集。

## 更新版本

```bash
git fetch origin --prune
git switch codex/handwriting-collector-deploy
git pull --ff-only origin codex/handwriting-collector-deploy
docker compose --env-file deploy/handwriting-collector/.env \
  -f deploy/handwriting-collector/compose.yaml up -d --build
docker image prune -f
```

## 查看状态和日志

```bash
docker compose --env-file deploy/handwriting-collector/.env \
  -f deploy/handwriting-collector/compose.yaml ps
docker compose --env-file deploy/handwriting-collector/.env \
  -f deploy/handwriting-collector/compose.yaml logs --tail=200 collector
```

## 停止与回滚

停止服务不会删除任何用户数据，因为当前容器不保存采集数据：

```bash
docker compose --env-file deploy/handwriting-collector/.env \
  -f deploy/handwriting-collector/compose.yaml down
```

正式发布时建议把 `COLLECTOR_TAG` 设置为 Git 提交号，并保留上一版本镜像。需要回滚时切换到上一提交，重新执行 `up -d --build`。

## 部署验收

1. `docker compose ps` 显示容器为 `healthy`。
2. HTTPS 地址可以在手机和平板上打开。
3. 初次测试可以生成 ID，后续测试可以恢复 ID。
4. 数位板接触时才产生轨迹，笔压会反映在线条粗细中。
5. 完成采集后能导出形如 `MT-24-A6V9-T003-202610171330.json` 的文件。
6. 服务器日志中没有参与者问卷答案、书写轨迹或导出的 JSON 内容。

## 后续自动上传

自动上传、服务器分配轮次和历史记录读取需要增加采集 API、数据库表、访问令牌和对象存储。当前部署包没有启用这些能力，因此服务器人员不需要配置数据库，也不会在服务器上留下参与者数据。
