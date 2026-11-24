# 采集端上传接收器（Windows）

本文说明仓库根目录的 [upload-server.ps1](../../upload-server.ps1)、[update-upload-server.ps1](../../update-upload-server.ps1) 和 [watch-mindtrace.ps1](../../watch-mindtrace.ps1) 如何接收最新采集端格式。

## 接口

- `POST /api/handwriting-sessions`
- `Content-Type: application/json; charset=utf-8`
- `X-Filename`：可选的原始文件名（URL 编码）
- `X-Upload-Token`：可选令牌；生产环境建议启用 `-RequireToken`
- `GET /health`：返回 `ok/service/time/requireToken/requireImageConsent/maxImageBytes/maxImageTotalBytes/maxImagesPerSession`

接收器按 UTF-8 原文保存完整 JSON，不剥离 `attempts`、图片或任何新字段。带图片的 session 会把 JSON 和 PNG 放在同一个 session 文件夹；无图片的旧包仍保持原来的单文件布局。

返回示例：

```json
{
  "ok": true,
  "storedAs": "MT-24-XXXX-T001/2026-11-22/MT-24-XXXX-T001-20261122/session.json",
  "bytes": 123456,
  "schemaVersion": "1.7.0",
  "images": 4,
  "imageBytes": 234567,
  "imageFiles": [
    "MT-24-XXXX-T001/2026-11-22/MT-24-XXXX-T001-20261122/session-COPY_SENTENCE_REPEAT_1-2.png"
  ]
}
```

## 存储布局

所有新上传统一为“人员 / 日期 / session”三级目录：

```text
uploads/<participant-id>/<yyyy-MM-dd>/<session-stem>/<safe-name>.json
uploads/<participant-id>/<yyyy-MM-dd>/<session-stem>/<attempt>.png
uploads/image-index.csv
```

- `participant-id` 来自 `payload.participantId`，做安全字符过滤；缺失时用 `unknown-participant`；
- 日期优先取 `collectionCompletedAt`，其次 `createdAt`/`exportedAt`，都缺失时用服务器当前日期；
- 同一个 session 的 JSON 和全部 PNG 在同一个 session 文件夹；
- 图片文件名来自 `attempts[].image.filename`，经过安全字符过滤和重名处理；
- `image-index.csv` 记录 `session_id/attempt_id/image_file/bytes/sha256/width/height`；
- `manifest-v2.csv` 的 `stored_as` 指向 session 文件夹里的 JSON；
- 无图片的 1.6/1.7/1.8 旧包也放进 session 文件夹，只是没有 PNG。

写入顺序是先写 PNG，再写 JSON，最后追加索引；如果 PNG 或 JSON 写入失败，会删除本次新建的 session 文件夹，避免留下半包。索引写入失败只记录日志，不删除已成功的 JSON/PNG。

部署前已经上传的图片 session 仍是“JSON 内嵌 base64、没有 PNG 文件”的旧布局；它们不会自动迁移。需要时用离线脚本解码 `attempts[].image.dataUrl` 到同一 session 文件夹，并补写 `image-index.csv`，不要重复上传或改写原始 JSON。

## 兼容的客户端格式

| schema | 客户端 | 说明 |
|---|---|---|
| 1.6.0 | 旧 18 题问卷 | 无图片，继续兼容 |
| 1.7.0 | WHO-5 | 最新 main 客户端增加 `attempts[].image` |
| 1.8.0 | yuyu 旧分支 | 设备档案/停顿指标；当前 main 分支未包含；接收器不按 schema 白名单拒绝 |

最新 main 客户端的图片字段：

```json
"attempts": [
  {
    "attemptId": "...",
    "points": [...],
    "image": {
      "filename": "<sessionId>-<taskId>-<n>.png",
      "mimeType": "image/png",
      "dataUrl": "data:image/png;base64,..."
    }
  }
]
```

## 图片校验

当请求包含任意 `attempt.image` 时，接收器会检查：

- `consent.accepted === true` 且 `consent.status === "granted"`；
- `filename` 只含安全字符、以 `.png` 结尾；
- `mimeType` 为 `image/png`；
- `dataUrl` 以 `data:image/png;base64,` 开头；
- base64 可解码、非空、单张 ≤ `-MaxImageBytes`（默认 8 MiB）；
- PNG 签名和 IHDR 合法；宽高 ≤ 4096 且像素数 ≤ 8,000,000；
- 每个 session 图片数 ≤ `-MaxImagesPerSession`（默认 12）；
- 解码后图片总字节 ≤ `-MaxImageTotalBytes`（默认 16 MiB）。

失败返回 422 或 413，错误码：

- `invalid_image_payload`
- `image_too_large`
- `too_many_images`
- `image_bytes_too_large`
- `consent_missing_or_not_granted`
- `consent_version_too_old`（严格模式）
- `consent_scope_missing`（严格模式）

接收器不会把 base64、图片内容或参与者数据写入日志；日志只记录计数、字节数和同意版本。

## 知情同意模式

当前 main 客户端的 `consent.version` 仍是 `local-anonymous-collection-v1.2`，scope 是 `demographics/research/model_development`，**没有显式包含服务器存储/图片上传**。因此接收器默认：

- 图片包必须 `accepted=true`；
- 但 v1.2 仍可接收，并在 `manifest-v2.csv` 记录 `consent_version=local-anonymous-collection-v1.2`；
- 监控会显示“旧同意版本”数量。这些图片记录在用于模型训练前应重新确认同意。

更严格的部署可加 `-RequireImageConsent`：要求 v1.3/v1.4 且 scope 包含 `server_storage`、`model_development`。启用前必须先把客户端同意书版本/scope 升上去，否则最新客户端会被拒绝。推荐客户端升级到类似：

```json
"consent": {
  "status": "granted",
  "accepted": true,
  "version": "local-anonymous-collection-v1.4",
  "dataUseScope": ["demographics", "research", "model_development", "server_storage", "image_upload"],
  "imageUploadDisclosed": true,
  "handwritingImageRecoverable": true
}
```

## manifest

- `manifest.csv`：兼容旧格式（日期、文件名、session、participant、eligibility、bytes）。
- `manifest-v2.csv`：新增 `schema_version/app_version/consent_version/consent_accepted/consent_scopes/attempts/images/image_bytes`，供审计和训练清单使用。

## 部署

仓库根目录的脚本来自实际 Windows 服务。更新时把 `upload-server.ps1`、`update-upload-server.ps1`、`watch-mindtrace.ps1` 放到独立更新目录，在服务器管理员 PowerShell 中：

```powershell
.\update-upload-server.ps1 -Root 'C:\yyh_project\mindtrace-collector' -WhatIf
.\update-upload-server.ps1 -Root 'C:\yyh_project\mindtrace-collector'
```

更新器会备份旧脚本、保留监听地址/数据目录/令牌/大小限制，只重启 `MindTraceUploadServer` 计划任务；健康检查要求新脚本返回 `maxImageBytes` 字段。已有上传、日志和静态网站任务不变。

## 监控

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'C:\yyh_project\mindtrace-collector\watch-mindtrace.ps1' -Once
```

窗口显示服务健康、令牌/图片同意模式、协议兼容、总文件数、今日写入、图片 session/张数/字节、旧同意版本数量、磁盘余量和最近失败类别。监控不读取 JSON 正文。

## 本地测试

```powershell
python -m pytest tests/test_collector_upload.py -q -p no:cacheprovider --basetemp=tmp/pytest-collector
```

测试只用合成包，不读取真实参与者数据。覆盖 1.6/1.7/1.8、图片合法/非法、同意缺失/拒绝/严格版本、图片数量、令牌、重复文件名、坏 JSON 和 CORS 预检。

## 安全建议

- 生产环境启用 `-RequireToken`，客户端构建配置同一 `VITE_UPLOAD_TOKEN`。
- 采集端默认上传地址是 `http://82.157.132.139:8082`；图片和轨迹属于敏感数据，正式采集应改为 HTTPS 反向代理，避免明文传输。
- 不要把 `uploads/`、`manifest*.csv`、日志或图片复制进 Git。
- 图片可能包含自由书写内容；访问权限、保留期限和删除流程按知情同意与伦理审批执行。
