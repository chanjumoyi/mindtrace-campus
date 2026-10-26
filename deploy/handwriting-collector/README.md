# 手写数据采集端部署包

本目录提供 `frontend/handwriting-collector-mobile` 的只读 Nginx 部署配置，配套的 Windows 采集上传脚本位于仓库根目录。客户端会在本机保存并导出 JSON，同时向配置的采集接口上传；静态 Nginx 容器本身不保存采集数据。

如需生成可安装的 Android APK/AAB，请参阅 [ANDROID.md](./ANDROID.md)。

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

## Windows 上传接收器

仓库根目录的[上传接收器](../../upload-server.ps1)来自此前单独存放于 `.rdp-deploy` 的实际 Windows 服务，接口为 `POST /api/handwriting-sessions`，默认端口 8082。接收完整 UTF-8 JSON 会话包，兼容 1.6 十八题问卷与 1.7 / 1.8 WHO-5；笔迹仍位于 `attempts[].points`。服务端按原文保存请求，返回 `{ "ok": true, "storedAs": "日期/文件名.json", "bytes": 123 }`，重名文件另存而不覆盖。

客户端未配置 `VITE_UPLOAD_TOKEN` 时会省略 `X-Upload-Token`。接收器默认允许这种请求；配置了服务端令牌后，显式提供错误令牌的请求仍返回 401。需要强制鉴权的部署可设置环境变量 `MINDTRACE_UPLOAD_TOKEN`，并使用 `-RequireToken` 启动；相应客户端构建必须配置同一 `VITE_UPLOAD_TOKEN`。仓库不包含生产令牌。

现有 Windows 部署位于 `C:\yyh_project\mindtrace-collector`。将仓库根目录的 `upload-server.ps1`、[更新脚本](../../update-upload-server.ps1)和[监控脚本](../../watch-mindtrace.ps1)复制或解压到独立更新目录，在服务器管理员 PowerShell 中执行：

```powershell
.\update-upload-server.ps1 -Root 'C:\yyh_project\mindtrace-collector'
```

更新器先备份原脚本，保留现有令牌、监听地址、上传目录与大小限制，再只重启 `MindTraceUploadServer` 计划任务；现有上传文件、日志和静态网站任务保持原样。可先加 `-WhatIf` 查看操作。若写入或启动任务失败，会恢复原脚本。

接口健康检查为 `GET /health`，响应中的 `requireToken` 表示是否启用强制令牌模式。默认请求体上限为 25 MiB，最低剩余空间为 300 MiB。

### Windows 服务监控

接收器更新脚本只更新上传服务。继续在独立更新目录中安装监控脚本；若已有同名脚本，先保留备份：

```powershell
$collectorRoot = 'C:\yyh_project\mindtrace-collector'
$monitorTarget = Join-Path $collectorRoot 'watch-mindtrace.ps1'
if (Test-Path -LiteralPath $monitorTarget) {
  Copy-Item -LiteralPath $monitorTarget -Destination ($monitorTarget + '.backup-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
}
Copy-Item -LiteralPath .\watch-mindtrace.ps1 -Destination $monitorTarget -Force
powershell.exe -NoProfile -ExecutionPolicy Bypass -NoExit -File $monitorTarget -Root $collectorRoot
```

首次替换服务器原有监控脚本后，关闭旧监控窗口，再用上述命令打开新监控。关闭监控不会停止后台网站或上传服务。新监控默认每 5 秒刷新，并在下次刷新时自动加载脚本更新；可用 `-RefreshSeconds 10` 调整间隔。

窗口显示网站和上传接口健康、计划任务状态、健康响应 `requireToken` 对应的上传鉴权模式、协议兼容说明、采集文件总数和今日写入数、总大小、磁盘余量、最近 5 个上传文件的时间与大小，以及最多 3 条失败类别。上传鉴权显示“默认允许无令牌上传”或“强制上传令牌”；旧服务或接口不可用时显示未知。监控不读取采集 JSON 正文，也不显示参与者文件名、令牌、IP 或原始日志。

需要单次检查时执行：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'C:\yyh_project\mindtrace-collector\watch-mindtrace.ps1' -Once
```

Windows 本地回归测试（只使用合成采集包）：

```powershell
python -m pytest tests/test_collector_upload.py -q -p no:cacheprovider
```
