# 笔迹模块 KWC 与 Qwen 接入

## 当前链路

```text
C 正式前端 / KWC 组件
  -> C Java 网关 /api/v1/handwriting/analyze
  -> A Python 服务 :8091
  -> 轨迹校验与可解释特征
  -> Qwen2.5-7B-Instruct 或安全 Mock
  -> 统一结果 Schema
```

前端和 KWC 不保存模型密钥，也不直接请求阿里云。Qwen 只接收结构化客观观察、引用和限制，不接收原始坐标轨迹或参与者自评标签。

## 本地 Mock 模式

Mock 不需要密钥：

```powershell
$env:HANDWRITING_LLM_MODE='mock'
python local\ai-lab\handwriting\service\server.py --port 8091
```

## Qwen2.5-7B 模式

在本机环境变量或未提交的 `.env` 中配置：

```text
HANDWRITING_LLM_MODE=qwen
QWEN_MODEL=qwen2.5-7b-instruct
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_API_KEY=你的密钥
QWEN_TIMEOUT_SECONDS=20
```

如果百炼工作空间已经提供专属域名，应优先把 `QWEN_BASE_URL` 换为控制台显示的区域专属 `/compatible-mode/v1` 地址。不要把真实 Key 写入 `.env.example`、源码、前端属性或 Git。

## 正式前端

C 控制台登录后，从“笔迹观察”进入页面：

1. 选择采集器导出的完整 JSON；
2. 浏览器本地预览轨迹；
3. 通过 Java 网关调用 Python 分析；
4. 展示数据质量、客观观察、Qwen/Mock 说明、证据和限制。

本地 Java 网关默认连接 `http://localhost:8091`。Docker Compose 内连接 `http://handwriting-service:8091`。

## 苍穹 KWC

业务组件位于 `kingdee/kwc-handwriting`。租户 KWC SDK 到位后，将其 `mount/update/unmount` 和 `KwcHostAdapter` 映射到实际平台版本，并把 `apiBaseUrl` 指向 C 的 Java 网关。

## 安全降级

- 未配置 Key：返回 `llmExplanation.status=DEGRADED` 或 Mock。
- Qwen 超时、网络错误、JSON 不合格：自动使用本地 Mock。
- 输出出现诊断或疾病定论词：拒绝模型输出并自动降级。
- 所有结果固定附带非诊断声明。
