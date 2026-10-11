# API 规范

状态：已按立项报告对齐
最后更新：2026-10-11

## 通用约定

- 基础前缀：`/api/v1`
- 数据格式：`application/json`
- 字段命名：`snake_case`
- 时间格式：带时区的 ISO 8601
- 鉴权：短期访问令牌与可撤销会话；受保护接口必须校验数据归属
- 分析接口：返回模型版本、置信度、依据、局限和降级状态

统一错误结构：

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "请求参数校验失败",
    "request_id": "req_xxx",
    "details": []
  }
}
```

## 接口清单

- 系统：`GET /health`、`GET /modules`
- 认证：`POST /auth/register`、`POST /auth/login`、`POST /auth/logout`、`GET /auth/me`
- 授权与数据权利：`GET|POST /consents`、`POST /account/export`、`DELETE /account`
- 情绪：`GET|POST /wellbeing/moods`、`GET /wellbeing/moods/trend`、`DELETE /wellbeing/moods/{id}`
- 手账：`GET|POST /wellbeing/journals`、`GET|PUT|DELETE /wellbeing/journals/{id}`
- 对话：`POST /ai/chat`、`GET /ai/health`、`GET /ai/sessions/{id}`
- 笔迹：`POST /handwriting/analyze`、`GET /handwriting/health`、`GET /handwriting/history`
- 房树人：`POST /htp/records`、`POST /htp/analyze`、`GET /htp/records/{id}`
- 沙盘：`POST /sandplay/records`、`POST /sandplay/analyze`、`GET /sandplay/records/{id}`
- 内容：`GET /wellbeing/resources`、`GET /wellbeing/resources/{id}`、`POST /wellbeing/progress`
- 推荐：`GET /recommendations`、`PUT /recommendations/preferences`
- 分析任务：`GET /analysis-jobs/{id}`、`POST /analysis-jobs/{id}/cancel`
- 分析结果：`GET /analysis-results/{id}`

## 契约要求

- 列表接口明确分页、过滤和排序。
- 写接口考虑重复提交和幂等。
- 上传内容限制类型、大小并进行恶意文件检查。
- LLM 超时、未配置或输出越界时使用可测试的安全降级响应。
- 耗时分析创建接口返回 `202 Accepted` 和任务标识，任务最终状态保存在 MySQL。
- 创建分析、数据导出和账号删除必须支持 `Idempotency-Key`。
- OpenAPI、JSON Schema、前端类型与自动化测试保持一致。

认证会话、任务状态机、错误格式和并发规则以[系统架构说明](../02-architecture/README.md)为准。
