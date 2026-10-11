# 心迹AI系统架构说明

版本：1.0

状态：已接受，作为开发基线

生效日期：2026-10-11

适用范围：心迹AI Web 平台、后端服务、AI 与算法模块、研究数据流程和本地部署

## 1 文档目的

本文档是心迹AI项目的规范性架构基线。后续需求拆分、目录设计、接口设计、数据库迁移、测试和部署必须以本文档为准。

本文使用以下约束词：

- **必须 MUST**：实现不得偏离；若需修改，必须先新增 ADR 并完成团队评审。
- **应该 SHOULD**：默认遵守；偏离时必须在代码评审中说明理由。
- **可以 MAY**：根据任务复杂度和阶段选择。

若其他项目文档与本文冲突，优先级依次为：伦理与安全要求、本文档、API 契约、模块说明、实现代码。立项报告定义项目目标和成果范围，本文定义软件如何实现这些目标。

## 2 架构结论

项目采用**研究型模块化单体**：

- 前端为一个 Vue 3 Web 应用。
- 后端为一个 FastAPI 代码库和一个 API 部署单元。
- 后台分析 Worker 与 API 使用同一份后端代码和同一套模块，不构成独立微服务。
- MySQL 保存账号、授权、业务记录、分析元数据和审计元数据。
- 图片、原始笔迹轨迹和导出包通过对象存储接口保存；开发阶段使用本地文件适配器，集成阶段切换到 S3 兼容存储。
- 所有外部大模型调用通过统一 LLM 网关，不允许业务模块直接请求模型供应商。
- 耗时分析通过统一任务接口执行；开发阶段可同步执行，集成阶段切换为 Celery Worker 与 Redis Broker，业务代码不随运行模式变化。
- `research/` 是离线研究区，只读取经过批准和去标识化的导出数据，不被线上 API 直接导入。
- 当前阶段不拆微服务，不引入 Kubernetes、Kafka、多套后端或多数据库。

该方案在保持部署简单的同时，为异步分析、对象存储、模型替换和研究复现预留稳定边界。

## 3 架构目标与优先级

发生取舍时，按以下顺序决策：

1. 用户安全、隐私和伦理合规。
2. 数据正确性、归属隔离和可删除性。
3. 核心流程可用与安全降级。
4. 研究可复现性和结果可解释性。
5. 可维护性和自动化测试。
6. 性能与扩展性。
7. 技术新颖性。

项目不以高并发或复杂基础设施为主要目标。任何新增技术组件必须解决已经出现的问题，而不是为假设的未来规模增加复杂度。

## 4 系统上下文

```mermaid
flowchart LR
    USER[大学生用户] --> WEB[心迹AI Web 应用]
    WEB --> API[心迹AI API]
    API --> DB[(MySQL)]
    API --> STORE[对象存储接口]
    API --> LLM[LLM 网关]
    LLM --> PROVIDER[DeepSeek 或兼容模型]
    API --> TASKS[任务调度接口]
    TASKS --> WORKER[分析 Worker]
    WORKER --> DB
    WORKER --> STORE
    WORKER --> LLM
    EXPORT[研究数据导出] --> RESEARCH[离线研究与评估]
    DB --> EXPORT
    STORE --> EXPORT
```

外部参与者只有大学生用户和经批准的研究人员。项目当前不建设辅导员工作台、管理员业务后台、预约审批或校园行政处置系统。

## 5 容器与部署单元

### 5.1 固定部署单元

| 单元 | 技术 | 职责 | 是否必需 |
| --- | --- | --- | --- |
| `frontend` | Vue 3、Vite、Nginx | 页面、交互、静态资源、API 反向代理 | 必需 |
| `api` | FastAPI、Uvicorn | 认证、业务 API、授权校验、任务提交 | 必需 |
| `mysql` | MySQL 8 | 结构化业务数据与元数据 | 必需 |
| `worker` | 与 API 相同的 Python 镜像 | 执行笔迹、房树人、沙盘和批量导出任务 | 集成阶段必需 |
| `redis` | Redis | Celery Broker；不作为业务事实来源 | 集成阶段必需 |
| `object-storage` | 本地目录或 S3 兼容服务 | 保存原始轨迹、图片和导出文件 | 接口必需，独立服务可选 |
| `llm-provider` | DeepSeek 或兼容 API | 对话和结构化解释 | 外部可选，必须可降级 |

### 5.2 开发拓扑

开发环境必须支持最小依赖启动：

```text
frontend + api + mysql
TASK_MODE=inline
OBJECT_STORAGE_DRIVER=local
LLM_MODE=mock 或 external
```

`inline` 只用于开发、自动化测试和小规模演示。业务服务仍必须通过 `TaskDispatcher` 提交任务，不得直接调用任务实现。

### 5.3 集成与用户测试拓扑

进入房树人、沙盘、批量笔迹分析或正式用户测试前，应切换为：

```text
frontend + api + worker + mysql + redis + S3-compatible storage
TASK_MODE=celery
OBJECT_STORAGE_DRIVER=s3
```

Redis 只传递任务，不保存最终状态。任务最终状态和结果索引必须写入 MySQL，因此 Redis 数据丢失后仍可识别并恢复未完成任务。

### 5.4 部署约束

- API 与 Worker 必须使用相同代码版本、Schema 版本和配置格式。
- 数据库迁移必须在 API 和 Worker 升级前完成。
- 生产或用户测试环境必须启用 HTTPS。
- MySQL、Redis 和对象存储不得直接暴露到公网。
- 开发、测试、演示和用户研究环境必须使用不同的数据库、存储桶和密钥。
- 不使用 `Base.metadata.create_all()` 管理正式环境 Schema；正式环境必须使用 Alembic 迁移。

## 6 逻辑模块

### 6.1 模块清单

| 模块 | 主要职责 | 拥有的数据 |
| --- | --- | --- |
| `identity` | 注册、登录、退出、密码、会话、当前用户 | users、auth_sessions |
| `consent` | 隐私说明、授权版本、撤回、导出和删除申请 | consent_records、privacy_requests |
| `wellbeing` | 心情、压力、睡眠记录和趋势 | mood_entries |
| `journal` | 电子手账 CRUD、分页和归属 | journal_entries |
| `chat` | 对话会话、多轮上下文、危机安全分流 | chat_sessions、chat_messages |
| `handwriting` | 轨迹接收、特征提取、质量评估和个人基线 | handwriting_sessions、handwriting_features |
| `htp` | 房树人绘制或上传、问卷、观察任务和结果 | htp_records |
| `sandplay` | 沙盘元素、布局、分析任务和回看 | sandplay_records、sandplay_elements |
| `content` | 冥想、瑜伽、心理科普及版本 | wellness_contents、content_progress |
| `recommendation` | 可解释推荐和用户偏好 | recommendation_records、recommendation_preferences |
| `analysis` | 通用分析任务、状态、结果索引和模型版本 | analysis_jobs、analysis_results |
| `audit` | 安全操作、授权变更和模型调用元数据 | audit_logs、model_call_logs |
| `research_export` | 去标识化导出、导出审批和数据清单 | export_jobs、export_manifests |

模块名称同时用于后端目录、API 标签、日志字段和任务名称。不得为同一概念创造第二套名称。

### 6.2 模块依赖规则

```mermaid
flowchart TD
    API[API 路由] --> APP[模块应用服务]
    APP --> DOMAIN[模块领域逻辑]
    APP --> REPO[模块仓储接口]
    APP --> PORTS[公共端口]
    REPO --> INFRA[数据库适配器]
    PORTS --> INFRA2[LLM 任务 存储适配器]
```

必须遵守：

1. 路由层只负责认证依赖、参数解析、调用应用服务和映射 HTTP 响应。
2. 路由层不得直接操作 SQLAlchemy Session、外部 LLM 或对象存储。
3. 领域逻辑不得依赖 FastAPI、SQLAlchemy、Celery、Redis、HTTP 客户端或供应商 SDK。
4. 一个模块不得直接导入另一个模块的 ORM Model 或 Repository。
5. 跨模块调用必须通过对方公开的 application service、只读查询接口或领域事件。
6. `shared` 只允许放置稳定的值对象、基础错误、分页类型和公共端口，不允许放置业务服务。
7. AI、任务和存储适配器必须通过依赖注入提供。

### 6.3 允许的跨模块调用

| 调用方 | 可调用模块 | 用途 |
| --- | --- | --- |
| 所有用户模块 | `identity` | 获取当前用户标识，不读取密码或会话细节 |
| 所有敏感模块 | `consent` | 校验当前授权范围 |
| `chat`、`handwriting`、`htp`、`sandplay` | `analysis` | 创建和查询分析任务 |
| `analysis` | AI 与算法公共端口 | 调用模型、特征服务和安全过滤 |
| `recommendation` | `wellbeing`、`content` 的只读查询 | 生成推荐依据 |
| `research_export` | 各模块只读导出接口 | 生成去标识化数据集 |
| 所有模块 | `audit` | 写入不含敏感正文的审计事件 |

禁止形成循环依赖。若两个模块互相调用，必须提取公共事件或重新确定数据所有权。

## 7 代码目录基线

### 7.1 后端

```text
backend/
├─ app/
│  ├─ main.py
│  ├─ api/
│  │  ├─ dependencies.py
│  │  └─ router.py
│  ├─ core/
│  │  ├─ config.py
│  │  ├─ database.py
│  │  ├─ errors.py
│  │  ├─ logging.py
│  │  ├─ security.py
│  │  └─ telemetry.py
│  ├─ shared/
│  │  ├─ pagination.py
│  │  ├─ types.py
│  │  └─ ports/
│  │     ├─ llm.py
│  │     ├─ object_storage.py
│  │     └─ task_dispatcher.py
│  ├─ modules/
│  │  ├─ identity/
│  │  ├─ consent/
│  │  ├─ wellbeing/
│  │  ├─ journal/
│  │  ├─ chat/
│  │  ├─ handwriting/
│  │  ├─ htp/
│  │  ├─ sandplay/
│  │  ├─ content/
│  │  ├─ recommendation/
│  │  ├─ analysis/
│  │  ├─ audit/
│  │  └─ research_export/
│  ├─ infrastructure/
│  │  ├─ llm/
│  │  ├─ storage/
│  │  ├─ tasks/
│  │  └─ crypto/
│  └─ workers/
│     └─ celery_app.py
├─ migrations/
├─ tests/
│  ├─ unit/
│  ├─ integration/
│  ├─ contract/
│  ├─ security/
│  └─ e2e/
├─ requirements.txt
└─ requirements-dev.txt
```

每个业务模块统一采用：

```text
module_name/
├─ api.py            # APIRouter 和 HTTP 映射
├─ schemas.py        # 请求与响应 Schema
├─ service.py        # 用例编排和事务边界
├─ domain.py         # 纯业务规则和值对象
├─ models.py         # 本模块 ORM Model
├─ repository.py     # 仓储接口与实现
├─ permissions.py    # 本模块授权规则
└─ tasks.py          # 可选的后台任务入口
```

简单模块可以省略空文件，但职责不得混合。现有的 `api/routes`、`models.py` 和 `schemas.py` 应按业务迭代逐步迁移，不进行一次性大重写。

### 7.2 前端

```text
frontend/src/
├─ app/
│  ├─ router/
│  ├─ stores/
│  └─ bootstrap/
├─ api/
│  ├─ client.js
│  ├─ errors.js
│  └─ generated/
├─ features/
│  ├─ auth/
│  ├─ consent/
│  ├─ wellbeing/
│  ├─ journal/
│  ├─ chat/
│  ├─ handwriting/
│  ├─ htp/
│  ├─ sandplay/
│  └─ content/
├─ shared/
│  ├─ components/
│  ├─ composables/
│  ├─ validation/
│  └─ styles/
├─ App.vue
└─ main.js
```

前端功能目录只能通过公共 API 客户端访问后端。不得在组件中拼接服务地址、直接处理令牌或复制后端错误码。

### 7.3 研究目录

```text
research/
├─ protocols/        # 研究方案、伦理和知情同意模板
├─ datasets/         # 只允许合成、公开或去标识化数据
├─ features/         # 离线特征构建
├─ experiments/      # 可复现实验配置
├─ evaluations/      # 指标、误差分析和安全评测
├─ prompts/          # Prompt 源文件与版本
├─ knowledge-base/   # 有来源和许可记录的知识
└─ artifacts/        # 不进入 Git 的模型和中间产物
```

线上代码不得导入 `research/experiments` 或训练脚本。需要进入产品的算法必须迁移到后端模块，补充版本、测试和安全检查。

## 8 数据架构

### 8.1 数据存储分工

| 数据类型 | 存储位置 | 示例 |
| --- | --- | --- |
| 结构化业务数据 | MySQL | 用户、授权、心情、手账元数据、任务状态 |
| 小型结构化分析结果 | MySQL JSON 或规范化表 | 特征摘要、证据、置信度、局限 |
| 大型或原始数据 | 对象存储 | 轨迹 JSON、绘画、沙盘快照、导出包 |
| 短期任务消息 | Redis | Celery 消息，不作为最终状态 |
| 模型和实验产物 | 研究产物目录或独立存储桶 | 权重、评估输出、特征缓存 |

MySQL 中只保存对象键、内容类型、大小、哈希、所有者、创建时间、保留策略和加密元数据，不保存大尺寸二进制正文。

### 8.2 数据分类

| 等级 | 数据 | 要求 |
| --- | --- | --- |
| L0 公开 | 已审核科普内容、公开素材 | 可缓存和公开分发 |
| L1 内部 | 配置元数据、非敏感运行指标 | 仅团队和服务访问 |
| L2 个人 | 账号、偏好、内容进度 | 鉴权、归属校验、可导出删除 |
| L3 高敏感 | 对话、手账、量表、笔迹、绘画、分析结果 | 最小采集、加密、严格审计、禁止普通日志 |
| L4 身份映射 | 研究参与者与真实身份映射 | 与研究数据物理或逻辑隔离，最小人员访问 |

### 8.3 主键与归属

- 对外资源标识必须使用不可预测的 UUID 或等效随机标识。
- 内部自增主键可以保留，但不得作为公开 API 的唯一标识。
- 所有 L2/L3 数据表必须包含 `user_id` 或明确的所有者关系。
- 查询和修改 L2/L3 数据必须在 Repository 或 Service 层同时加入所有者条件，禁止先按 ID 查询再单独判断。
- 研究数据使用独立 `participant_code`，不得直接复用用户学号、手机号或数据库主键。

### 8.4 时间与版本

- 数据库存储 UTC 时间，API 返回带时区的 ISO 8601。
- 每个可变业务记录至少包含 `created_at`、`updated_at`。
- 软删除只用于需要恢复或审计的场景；用户数据删除请求最终必须执行物理删除或不可逆去标识化。
- 分析结果必须保存 `schema_version`、`feature_version`、`model_version`、`prompt_version` 和 `safety_policy_version`。

### 8.5 事务规则

- 一个 HTTP 写请求只能由一个应用服务拥有事务边界。
- 数据库事务中不得执行外部 LLM 请求、长时间文件处理或网络上传。
- 创建异步分析时，先在同一事务中保存业务记录和 `analysis_job`，提交后再投递任务。
- 若投递失败，任务保持 `PENDING` 并由恢复任务重新投递。
- Worker 必须使用幂等键，重复执行不得产生第二份业务结果。

### 8.6 对象存储键

对象键必须由服务生成，不使用用户原始文件名：

```text
users/{user_uuid}/{module}/{yyyy}/{mm}/{object_uuid}.{ext}
research-exports/{export_uuid}/{filename}
```

数据库记录保存 SHA-256 哈希。上传、下载和删除都必须经过业务授权；对象存储桶不得公开。

## 9 API 架构

### 9.1 基本规范

- 业务 API 固定前缀为 `/api/v1`。
- 请求和响应使用 JSON；文件上传使用受限的 `multipart/form-data` 或预签名上传流程。
- 字段使用 `snake_case`。
- OpenAPI 是 HTTP 契约源，前端类型应由契约生成或经过自动一致性检查。
- 不在 URL 中暴露用户学号、手机号或参与者编号。
- 列表接口使用游标或页码分页，并明确默认排序。

### 9.2 认证与会话

- Web 端采用服务端可撤销会话。
- 会话标识通过 `HttpOnly` Cookie 传递，用户脚本不得读取。
- 用户测试或正式环境必须设置 `Secure` 和合适的 `SameSite` 属性。
- 修改数据的请求必须实施同源检查和 CSRF 防护。
- 密码必须使用成熟的自适应密码哈希算法，不保存或记录明文密码。
- 退出登录、修改密码和删除账号必须撤销相关会话。

### 9.3 统一成功与错误

成功响应直接返回资源或分页对象。错误统一为：

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "未找到请求的资源",
    "request_id": "req_01...",
    "details": []
  }
}
```

错误码属于稳定契约，不以 Python 异常名或第三方错误信息作为公开错误码。5xx 响应不得泄露堆栈、SQL、密钥、Prompt 或上游响应正文。

### 9.4 幂等与并发

- 创建分析、数据导出和账号删除必须支持 `Idempotency-Key`。
- 普通表单提交应在前端防重复，后端仍需保证幂等或明确冲突响应。
- 可编辑资源使用 `updated_at` 或版本号进行乐观并发控制。
- 重复的任务回调和 Worker 重试必须安全。

### 9.5 分析任务 API

耗时分析统一采用异步资源模型：

```text
POST /api/v1/{module}/analyses          创建任务，返回 202
GET  /api/v1/analysis-jobs/{id}         查询任务状态
GET  /api/v1/analysis-results/{id}      获取结果
POST /api/v1/analysis-jobs/{id}/cancel  请求取消
```

开发模式可以在同一请求内完成任务，但响应 Schema 和任务记录不得改变。

## 10 异步任务架构

### 10.1 任务状态机

```mermaid
stateDiagram-v2
    [*] --> PENDING
    PENDING --> RUNNING
    PENDING --> CANCELLED
    RUNNING --> SUCCESS
    RUNNING --> DEGRADED
    RUNNING --> FAILED
    RUNNING --> CANCEL_REQUESTED
    CANCEL_REQUESTED --> CANCELLED
    CANCEL_REQUESTED --> SUCCESS: 已进入不可中断阶段
    FAILED --> PENDING: 满足重试策略
```

状态含义：

- `PENDING`：数据库记录已创建，等待执行。
- `RUNNING`：Worker 已获得任务租约。
- `SUCCESS`：按目标流程完成。
- `DEGRADED`：本地结果可用，但外部模型或非关键步骤失败。
- `FAILED`：没有可交付结果，且本轮不再自动重试。
- `CANCEL_REQUESTED`：用户请求取消，Worker 应在安全点停止。
- `CANCELLED`：任务未执行或已安全终止。

### 10.2 任务实现规则

- 每个任务必须有唯一任务类型、Schema 版本和幂等键。
- Worker 从数据库读取真实输入位置，不把敏感正文完整放入 Redis 消息。
- 任务消息只包含 `job_id`、任务类型和追踪标识。
- 任务必须设置超时、有限重试和指数退避。
- 校验错误和安全越界不得自动重试。
- 上游超时、限流和临时 5xx 可以重试。
- Worker 写结果前必须再次确认任务所有者、状态和 Schema 版本。

### 10.3 任务适配器

业务模块只依赖：

```python
class TaskDispatcher(Protocol):
    def dispatch(self, job_id: str, task_type: str) -> None: ...
```

必须提供：

- `InlineTaskDispatcher`：开发和测试使用。
- `CeleryTaskDispatcher`：集成、演示和用户测试使用，Redis 作为 Broker。

切换适配器只能修改环境变量和依赖注入配置，不修改业务服务。

## 11 AI 与算法架构

### 11.1 统一 LLM 网关

所有 LLM 调用必须经过 `LlmGateway`，网关负责：

- 供应商和模型选择。
- 超时、有限重试和限流处理。
- Prompt 模板和版本加载。
- 输入最小化和去标识化。
- 结构化输出校验。
- 禁止词、越界结论和安全规则检查。
- 调用元数据审计。
- Mock 和安全降级。

业务模块不得读取 `DEEPSEEK_API_KEY`，不得自行构造供应商 URL，也不得直接解析供应商响应。

### 11.2 标准分析结果

笔迹、房树人、沙盘和多模态分析必须映射到统一外层结构：

```json
{
  "status": "SUCCESS",
  "summary": "非诊断性的客观摘要",
  "evidence": [],
  "confidence": 0.62,
  "limitations": [],
  "exploration_questions": [],
  "versions": {
    "schema": "1.0.0",
    "feature": "handwriting-feature@0.2.0",
    "model": "model-name@version",
    "prompt": "prompt-name@version",
    "safety_policy": "safety@1.0.0"
  }
}
```

模块可以在 `evidence` 中定义自己的结构，但不得删除外层字段。

### 11.3 安全处理流水线

```text
输入校验
  → 授权范围检查
  → 敏感信息最小化
  → 本地特征提取
  → LLM 结构化生成
  → Schema 校验
  → 医疗诊断与越界规则检查
  → 安全降级或发布结果
  → 记录不含正文的审计元数据
```

任何步骤失败都不得丢失已经完成且安全的本地分析。外部 LLM 失败时，优先返回 `DEGRADED` 和本地可解释结果。

### 11.4 Prompt 与模型版本

- Prompt 源文件进入 Git，禁止把长 Prompt 散落在路由和 service 中。
- Prompt 修改必须更新版本，并有结构化输出测试和安全回归测试。
- 模型产物不得直接提交 Git；仓库保存 manifest、哈希、训练配置和评估报告。
- 同一分析结果不得在没有新版本记录的情况下被后台静默重算。

### 11.5 危机表达边界

- 系统可以识别明显的紧迫风险表达并展示求助路径，但不得声称完成医学风险评估。
- 当前项目没有辅导员后台，因此不得设计“系统自动通知辅导员”的隐含流程。
- 是否记录高风险事件、记录哪些字段以及由谁复核，必须在伦理方案和用户知情同意中明确后才能启用。
- 危机响应必须在 LLM 不可用时仍可执行，不能只依赖生成模型。

## 12 对象存储架构

业务代码只依赖：

```python
class ObjectStorage(Protocol):
    def put(self, key: str, content: BinaryIO, metadata: dict) -> StoredObject: ...
    def open(self, key: str) -> BinaryIO: ...
    def delete(self, key: str) -> None: ...
    def exists(self, key: str) -> bool: ...
```

适配器：

- `LocalObjectStorage`：仅开发和自动化测试。
- `S3ObjectStorage`：集成、演示和用户测试，可连接 MinIO 或其他 S3 兼容服务。

上传流程必须验证大小、扩展名、MIME 类型、图片解码结果和哈希。用户提供的原始文件名只作为经过清理的显示信息，不作为对象键。

## 13 安全与隐私架构

### 13.1 基本原则

- 默认不采集不是核心功能所必需的数据。
- 默认不公开、不跨用户共享、不用于训练。
- 授权必须明确用途、数据类别、保留方式和撤回影响。
- 撤回授权后停止后续处理；已有数据按政策删除或去标识化。
- 真实参与者数据不得进入 Git、普通测试夹具、截图或日志。

### 13.2 加密

- 网络传输使用 TLS。
- 数据库和对象存储卷应使用部署环境提供的静态加密。
- 对话、手账、问卷自由文本和身份映射应通过应用层加密服务保护。
- 应用层加密使用成熟库提供的认证加密算法；密钥从部署 Secret 注入，不写入数据库或仓库。
- 密钥轮换必须通过版本化密钥标识完成，不原地覆盖而无法解密旧数据。

### 13.3 日志限制

禁止记录：

- 密码、Cookie、访问令牌和 API Key。
- 对话、手账、量表、笔迹、绘画和沙盘正文。
- LLM 完整 Prompt 和完整响应。
- 真实姓名、学号、手机号和身份映射。

允许记录：

- `request_id`、匿名用户内部标识、模块、路由、状态码和耗时。
- 任务类型、任务状态、模型版本、Token 用量和安全规则命中编号。
- 经过聚合且无法识别个人的运行指标。

### 13.4 数据导出与删除

- 用户导出和删除是后台任务，必须有幂等键和审计记录。
- 删除流程必须覆盖 MySQL、对象存储、缓存、未完成任务和身份映射。
- 备份中的删除采用保留期和恢复后重放删除清单的方式处理。
- 研究数据已经不可逆去标识化时，应在知情同意中说明其不可回溯删除边界。

## 14 配置基线

环境变量按职责分组，代码只通过集中配置对象读取：

```dotenv
APP_ENV=development
APP_SECRET_KEY=
PUBLIC_BASE_URL=http://localhost:8080
CORS_ORIGINS=http://localhost:5173,http://localhost:8080

DATABASE_URL=mysql+pymysql://user:password@mysql:3306/mindline

SESSION_COOKIE_NAME=mindline_session
SESSION_TTL_SECONDS=86400
FIELD_ENCRYPTION_KEY=

LLM_MODE=mock
LLM_PROVIDER=deepseek
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
LLM_API_KEY=
LLM_TIMEOUT_SECONDS=20
LLM_MAX_ATTEMPTS=3

TASK_MODE=inline
REDIS_URL=redis://redis:6379/0

OBJECT_STORAGE_DRIVER=local
OBJECT_STORAGE_LOCAL_ROOT=/data/objects
S3_ENDPOINT_URL=
S3_REGION=us-east-1
S3_BUCKET=mindline-private
S3_ACCESS_KEY=
S3_SECRET_KEY=
S3_USE_SSL=true

LOG_LEVEL=INFO
LOG_JSON=true
```

约束：

- `.env.example` 只包含安全占位符。
- 测试不得读取开发者真实 `.env`。
- 配置启动时完成校验；正式环境缺少必要密钥必须拒绝启动。
- 供应商专用变量只允许在 infrastructure 层使用。

## 15 可观测性与可靠性

### 15.1 请求追踪

- 每个请求生成或接受合法的 `X-Request-ID`。
- API、Worker、LLM 调用和对象操作使用同一追踪标识。
- 错误响应向用户返回 `request_id`，方便定位但不暴露内部细节。

### 15.2 指标

至少记录：

- API 请求量、错误率和 P50/P95 延迟。
- 任务队列长度、排队时间、执行时间和各状态数量。
- LLM 成功率、超时率、降级率和 Token 用量。
- 数据库连接、慢查询和迁移版本。
- 对象上传失败率和存储容量。
- 安全规则触发数量，不记录触发原文。

### 15.3 健康检查

- `/health/live`：进程存活，不检查外部依赖。
- `/health/ready`：检查数据库和必要配置；外部 LLM 失败不使 API 整体不就绪。
- Worker 必须提供可观察的心跳或最后成功任务时间。

### 15.4 可靠性策略

- 外部 LLM 失败时降级，不使手账、情绪记录和本地特征功能不可用。
- 数据库写入失败不得返回成功。
- 所有自动重试必须有限，并区分可重试与不可重试错误。
- 任务超时后必须进入明确状态，不能永久停留在 `RUNNING`。
- 每次用户测试前执行数据库和对象存储备份，并至少完成一次恢复演练。

## 16 测试架构

| 层级 | 目标 | 依赖 |
| --- | --- | --- |
| 单元测试 | 领域规则、特征算法、权限判断、状态机 | 无网络、无真实数据库 |
| 集成测试 | Repository、迁移、对象存储适配器、任务适配器 | 临时 MySQL/Redis/存储 |
| 契约测试 | OpenAPI、JSON Schema、错误码、LLM 结构化输出 | Mock 外部模型 |
| 安全测试 | 越权、注入、上传、隐私日志、Prompt 注入 | 隔离测试环境 |
| 端到端测试 | 注册到删除的核心用户流程 | 完整容器环境 |
| 研究评估 | 模型指标、误差分析、校准和分组表现 | 固定数据集和实验配置 |

测试要求：

- 外部 LLM 不进入默认 CI；CI 使用确定性 Mock。
- 每个模块至少包含成功、校验失败、未认证、越权和依赖降级测试。
- 每个数据库迁移包含升级验证；破坏性迁移必须说明回滚或数据迁移方案。
- 安全测试确认日志中不存在敏感正文。
- 算法评估与产品端到端测试分开，不能用页面可运行代替模型有效性证据。

## 17 CI 与质量门禁

每个合并请求必须通过：

1. Python 格式与静态检查。
2. 后端单元和集成测试。
3. 前端格式检查和生产构建。
4. JSON Schema、OpenAPI 和前端类型一致性检查。
5. 密钥和敏感数据扫描。
6. 依赖漏洞检查。
7. 数据库迁移检查。

涉及 AI、隐私或安全边界的改动还必须通过对应安全测试集。主分支不得在失败状态下发布。

## 18 开发流程

### 18.1 新增功能

1. 在产品文档确认范围、用户价值和非目标。
2. 确定数据所有权和所属模块。
3. 先定义 Schema、错误码、权限和验收测试。
4. 实现领域规则与应用服务。
5. 实现 Repository 和外部适配器。
6. 接入 API 与前端。
7. 增加单元、集成、权限、降级和端到端测试。
8. 更新 API、数据和模块文档。

### 18.2 Definition of Done

功能只有在以下条件全部满足时才算完成：

- 有明确用户和数据所有者。
- 服务端完成鉴权、归属和授权校验。
- 正常、空数据、错误和依赖失败状态都有可用体验。
- 不在日志中泄露敏感数据。
- 外部 LLM 不可用时有明确行为。
- 数据可以按用户请求导出和删除，或有书面例外说明。
- 自动化测试通过。
- Schema、模型、Prompt 和安全策略版本已记录。
- 文档与实际实现一致。

## 19 分阶段实施顺序

### 阶段 A 架构底座

- 建立模块目录和统一配置。
- 引入 Alembic，停止依赖自动建表。
- 完成统一错误、请求 ID、结构化日志和健康检查。
- 建立身份、会话、授权和数据归属。
- 建立 LLM、任务和对象存储三个公共端口及 Mock/本地适配器。

### 阶段 B 核心闭环

- 完成电子手账和情绪记录 CRUD、趋势和删除。
- 完成多轮对话、危机提示、Mock 降级和调用审计。
- 将现有笔迹算法迁入 `handwriting` 模块并接入前端。
- 完成用户数据导出与删除流程。

### 阶段 C 研究模块

- 建立 `analysis_job` 状态机。
- 接入 Worker、Redis 和 S3 适配器。
- 完成房树人和沙盘的结构化采集与回看。
- 完成文本与笔迹的离线多模态基线，不直接承诺上线推断。

### 阶段 D 用户测试与结项

- 建立去标识化研究导出。
- 完成安全评测、模型评估、可用性测试和备份恢复演练。
- 根据伦理审批范围进行用户测试。
- 固化演示环境、研究报告和结项材料。

不得在阶段 A 未完成时同时扩展多个研究模块。

## 20 架构变更规则

以下变化必须新增 ADR：

- 拆分微服务或新增独立后端语言。
- 更换数据库、任务系统、对象存储协议或认证方式。
- 改变模块的数据所有权。
- 新增真实参与者数据类别或改变数据用途。
- 允许自动通知第三方或自动形成高风险处置结论。
- 改变标准分析结果外层 Schema。

以下变化通常不需要 ADR：

- 模块内部重构但不改变公开接口和数据所有权。
- 新增符合现有端口的 LLM、存储或任务适配器。
- 新增 API 字段且保持向后兼容。
- 调整页面布局、文案和不影响数据语义的交互。

任何架构变更必须说明动机、替代方案、数据迁移、测试影响、安全影响和回滚方案。

## 21 明确不采用的方案

- 当前不拆分认证、AI、笔迹或内容微服务。
- 当前不使用 Kubernetes、服务网格、Kafka 或事件流平台。
- 当前不建设 Java/Spring Boot 第二套后端。
- 当前不让前端直接调用 LLM 或对象存储管理接口。
- 当前不把 Redis 当作业务数据库。
- 当前不把大型图片、轨迹或导出包直接保存为 MySQL BLOB。
- 当前不让线上服务直接运行训练脚本。
- 当前不承诺基于笔迹、房树人或沙盘进行医学诊断。

## 22 仍需由研究或伦理决定的参数

以下项目采用配置和策略表实现，不改变本文架构：

- 各类数据的具体保留期限。
- 量表使用条件和展示方式。
- 用户研究招募、补偿和退出流程。
- 高风险表达是否保存、保存哪些元数据以及复核人员。
- 多模态模型是否达到进入产品反馈的指标门槛。
- 科普、冥想和瑜伽内容的专业审核流程。

在这些参数确定前，系统使用最小采集、默认关闭研究用途和非诊断性输出。

## 23 架构验收清单

首次完整架构验收应确认：

- [ ] 前端、API 和数据库可以通过 Docker Compose 启动。
- [ ] 后端按模块组织，路由不直接访问 ORM 或外部服务。
- [ ] Alembic 可以从空数据库升级到最新版本。
- [ ] 用户只能读取和修改自己的数据。
- [ ] LLM、任务和对象存储均可在 Mock/本地模式运行。
- [ ] 外部 LLM 失败时核心记录功能仍可用。
- [ ] 分析任务状态可查询、可重试且幂等。
- [ ] 原始轨迹和图片不存入 MySQL BLOB。
- [ ] 日志扫描未发现敏感正文或密钥。
- [ ] 用户数据可以导出和删除。
- [ ] 研究导出不包含直接身份标识。
- [ ] 前后端构建、自动化测试和安全检查全部通过。

完成以上清单后，本文档所定义的方案二才算真正落地。
