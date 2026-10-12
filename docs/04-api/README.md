# API 规范

状态：当前接口与目标接口并列管理
最后更新：2026-10-12

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

## 当前已实现接口

- 系统：`GET /health`、`GET /api/v1/modules`
- 情绪：`GET|POST /api/v1/wellbeing/moods`
- 手账：`GET|POST /api/v1/wellbeing/journals`
- 内容：`GET /api/v1/wellbeing/resources`
- 对话：`POST /api/v1/ai/chat`、`GET /api/v1/ai/health`
- 笔迹：`POST /api/v1/handwriting/analyze`、`GET /api/v1/handwriting/health`

当前接口属于原型，认证、数据归属、分页、数据库迁移和统一错误尚未全部完成。修改原型接口时应迁入架构文档规定的模块目录，不再扩大扁平路由。

## 目标接口

- 系统：`GET /health`、`GET /api/v1/modules`
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
