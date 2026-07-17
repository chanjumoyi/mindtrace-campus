# 本地 Mock Agent

仅用于验证 C 负责的 AI 调用治理：超时、重试、幂等、requestId 和日志。它不包含 B 负责的 Agent Prompt、RAG、房树人或沙盘逻辑。

```bash
npm start
curl http://localhost:8090/health
```
