# A/B 模块接入指南

## 模块代码

- A：`HANDWRITING`
- B：`MULTIMODAL_AGENT`
- C：`COMMON`

## 请求规范

- `Authorization: Bearer <token>`
- `X-Request-Id: <uuid>`
- 写型 AI/工具调用：`Idempotency-Key: <stable-key>`
- 响应统一为：`success/code/message/data/requestId/timestamp`

## A 接入

A 自行实现笔迹采集页面、轨迹质量、特征、模型推理和结果展示。推荐流程：

1. 页面或服务上传笔迹相关文件到 `/files?moduleCode=HANDWRITING`，或只保存引用。
2. 创建 `/tasks`：`moduleCode=HANDWRITING`、`taskType=HANDWRITING_ANALYSIS`。
3. A 服务执行算法并按 `/tasks/{id}/status` 更新。
4. 业务结果保存在 A 的表/服务，`resultRef` 只放引用，不放完整敏感结论。
5. 管理员注册 A 的 Base URL 和契约版本。

## B 接入

B 自行实现房树人/沙盘页面、特征、Prompt、RAG、Agent 工作流和结果展示。推荐流程：

1. 文件使用 `/files?moduleCode=MULTIMODAL_AGENT`。
2. 异步分析使用通用任务状态。
3. 需要统一模型出口时调用 `/ai/invoke`；真实 Agent 服务替换 Mock Agent 的 Base URL。
4. B 必须在自己的契约中区分客观观察、用户解释、AI 推测和建议行动。
5. C 只负责注册工具和部署，不改 B 的 Prompt/知识库。

## 禁止事项

- 不得复制 `app_user` 或另建登录令牌。
- 不得将图片、轨迹、对话原文写入 `audit_log` 或 `ai_call_log`。
- 不得在前端存模型密钥。
- 不得直接修改 C 的初始迁移；公共变更需新增迁移并交叉评审。
