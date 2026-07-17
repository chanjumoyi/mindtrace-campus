# 心迹AI C：公共基础与苍穹集成

版本：1.0.0  
负责人边界：C  
交付范围：公共框架 + 数据底座 + 苍穹适配 + 系统集成

## 1. 本压缩包完成了什么

严格按《三人分工》实现 C 的任务：

- 公共页面：登录、首页、导航、个人中心、任务状态、文件中心、模块集成、审计日志。
- Java 统一网关和公共 DTO/API Envelope。
- PostgreSQL 公共数据模型与 Flyway 迁移。
- 用户、角色、权限、会话、审计、通用任务状态、文件对象、模块注册。
- AI 调用统一治理：超时、重试、幂等、每用户限流、requestId、摘要日志、失败回退。
- 本地 Mock Agent：只验证基础设施行为。
- KWC 公共组件规范、生命周期、Host Adapter、API Client、主题 Token。
- 苍穹公共领域模型清单、工具注册清单、Java 插件核心和部署迁移文档。
- Docker Compose 一键演示环境、模拟账号、接口契约、测试和回滚说明。

明确没有实现：

- A 的笔迹 Canvas、笔迹特征、模型训练/推理、笔迹结果页面。
- B 的房树人/沙盘页面、视觉或几何特征、Prompt、RAG、Agent 工作流、AI 评测。

上述模块只保留 `HANDWRITING` 和 `MULTIMODAL_AGENT` 注册位，方便后续合并。

## 2. 目录结构

```text
xinji-c-foundation/
├─ local/
│  ├─ backend/       Spring Boot 公共网关
│  ├─ frontend/      无依赖公共页面
│  └─ mock-agent/    基础设施 Mock Agent
├─ contracts/        OpenAPI 与 JSON Schema
├─ db/               概念—苍穹—数据库—API 映射
├─ kingdee/
│  ├─ domain-models/ 苍穹公共领域模型清单
│  ├─ agent-tools/   Agent 工具注册清单
│  ├─ kwc-common/    KWC 公共规范与适配器
│  ├─ java-plugin/   可编译插件核心 + 租户包装模板
│  └─ deployment/    安装包清单
├─ docs/             设计、合并、部署、权限、测试文档
├─ scripts/          启停、静态验证、烟测脚本
└─ docker-compose.yml
```

## 3. 最快使用方式：Docker Compose

### 3.1 前置条件

- Docker Engine 24+ 或兼容版本。
- Docker Compose v2。
- 建议至少 4GB 可用内存。
- 端口 `5432`、`8080`、`8088`、`8090` 未被占用；占用时修改 `docker-compose.yml` 左侧端口。

### 3.2 启动

在项目根目录执行：

```bash
cp .env.example .env
```

务必修改 `.env` 中的数据库和演示密码，然后执行：

```bash
./scripts/start.sh
```

也可以直接执行：

```bash
docker compose up --build -d
```

### 3.3 访问

- 公共前端：`http://localhost:8088`
- 后端健康检查：`http://localhost:8080/actuator/health`
- Mock Agent 健康检查：`http://localhost:8090/health`
- OpenAPI 文件：`contracts/openapi.yaml`

默认模拟账号（可由 `.env` 覆盖）：

| 角色 | 用户名 | 默认密码 |
|---|---|---|
| 学生 | `student_demo` | `demo123` |
| 咨询师 | `counselor_demo` | `demo123` |
| 系统管理员 | `admin_demo` | `admin123` |

这些账号只用于比赛模拟环境，禁止用于真实部署。

### 3.4 验证功能

1. 用学生账号登录，进入“任务状态”，创建 `COMMON` 任务并执行“开始→完成”。
2. 进入“文件中心”，上传 TXT/JSON/PNG/PDF，查看 SHA-256 和敏感级别，再下载验证。
3. 进入“个人中心”修改显示名称。
4. 用管理员登录，在“模块集成”中维护 A/B 的 Base URL 和契约版本。
5. 在同页测试 Mock Agent：
   - `echo`：一次成功。
   - `simulate-error`：前两次失败，第三次成功，用于验证重试。
   - `simulate-timeout`：触发超时和失败回退。
6. 打开“审计日志”，检查登录、任务、文件、模块和 AI 调用均有 requestId。
7. 执行自动烟测：

```bash
./scripts/smoke-test.sh
```

### 3.5 停止与清理

仅停止：

```bash
./scripts/stop.sh
```

停止并删除数据库/文件卷：

```bash
docker compose down -v
```

`-v` 会删除全部演示数据，请谨慎使用。

## 4. 不使用 Docker 的本地运行

### 4.1 PostgreSQL

创建数据库和用户：

```sql
CREATE USER xinji WITH PASSWORD 'your_password';
CREATE DATABASE xinji OWNER xinji;
```

### 4.2 Mock Agent

```bash
cd local/mock-agent
node server.js
```

需要 Node.js 20+，没有第三方 npm 依赖。

### 4.3 后端

需要 JDK 17+、Maven 3.6.3+：

```bash
cd local/backend
export DB_URL='jdbc:postgresql://localhost:5432/xinji'
export DB_USERNAME='xinji'
export DB_PASSWORD='your_password'
export APP_AGENT_BASE_URL='http://localhost:8090'
mvn spring-boot:run
```

首次启动由 Flyway 建表，初始化器创建角色、权限、模拟账号和三个模块注册位。

运行测试：

```bash
mvn test
```

### 4.4 前端

前端是原生 HTML/CSS/ES Modules，无构建依赖：

```bash
cd local/frontend
python3 -m http.server 5173
```

此时后端的 `APP_CORS_ALLOWED_ORIGINS` 应包含 `http://localhost:5173`。前端默认请求 `/api/v1`；直接用静态服务器时可通过反向代理，或在 `index.html` 之前注入：

```html
<script>window.XINJI_API_PREFIX='http://localhost:8080/api/v1'</script>
```

## 5. A/B 如何合并

A、B 不应修改 C 的核心表或复制认证逻辑。请阅读 `docs/AB模块接入指南.md`，主要步骤是：

1. A 使用 `moduleCode=HANDWRITING`，B 使用 `moduleCode=MULTIMODAL_AGENT`。
2. 各自维护业务页面、业务表、算法/Agent 服务。
3. 使用 C 的 Bearer 鉴权、统一 Envelope、requestId 和错误码。
4. 异步分析用 `/tasks` 记录状态；文件元数据用 `/files`；AI 出口用 `/ai/invoke`。
5. 管理员在 `/modules/{moduleCode}` 登记各自 Base URL 和契约版本。
6. 先修改 `contracts/` 再修改实现，禁止直接临时加字段。

## 6. 苍穹环境迁移

详见 `docs/苍穹部署与迁移.md`。推荐顺序：

1. 填写 `docs/环境基线.md`，确认租户、平台版本、KWC 版本、Java SDK/JDK、模型和产品包格式。
2. 按 `kingdee/domain-models/common-foundation-models.yaml` 建 C 的公共领域模型。
3. 配置角色和数据权限，验证系统管理员不能读取心理业务正文。
4. 导入/注册 `contracts/openapi.yaml` 对应服务模型。
5. 用官方开发工具生成实际 SDK 的最小插件包装层，复用 `kingdee/java-plugin/FoundationPluginCore.java`。
6. 实现 `KwcHostAdapter`，将公共页面/组件挂入苍穹；不要重写业务组件。
7. 按 `kingdee/agent-tools/tool-registration.yaml` 注册 C 已实现工具，以及 A/B 完成后的预留工具。
8. 导出产品安装包，在干净租户执行安装、初始化、升级、回滚验证。

当前压缩包没有硬编码某个未知版本的苍穹 SDK 类名或坐标。提供实际租户 SDK 后，只需完成薄包装，不需要重写网关和数据库逻辑。

## 7. 安全说明

- 访问令牌以 SHA-256 摘要存数据库，明文令牌只返回一次并保存在浏览器 `sessionStorage`。
- 密码使用 BCrypt；生产环境必须关闭或修改模拟账号。
- AI 日志只保存输入/输出摘要，不保存原始心理内容。
- 文件使用随机存储名、路径规范化、类型白名单和 SHA-256；生产需接入恶意文件扫描和对象存储。
- 写操作 AI 网关要求 `Idempotency-Key`，同键不同请求会拒绝。
- 本项目不提供医学诊断；所有数据均为模拟数据。

## 8. 验证与已知环境限制

`scripts/verify.sh` 会检查 JavaScript 语法、JSON/YAML、Java 源码基本结构并编译 JDK-only 的苍穹插件核心；检测到 Maven 时会执行后端测试。

生成本交付物的容器环境没有 Maven/Docker 且无法联网下载依赖，因此未在该容器中完成 Spring Boot 依赖编译和 Docker 镜像构建；代码包含 Maven 集成测试与 Docker 构建链，需在具备网络或依赖缓存的开发机执行 `./scripts/verify.sh` 和 `docker compose up --build` 完成最终环境验证。
