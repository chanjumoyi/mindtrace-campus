# C 任务完成与苍穹部署操作手册

版本：1.1.0
范围：仅 C 的公共框架、Java 网关、数据库、权限审计、KWC 公共组件、苍穹适配、部署和验收。
明确不包含：A 的笔迹页面/模型/推理，B 的房树人、沙盘、Prompt、RAG、Agent 工作流业务实现。

## 0. 当前事实和边界

1. 语雀链接在未登录抓取时返回 403，因此本仓库不能自动复制其中的私有教程内容。
2. 开发者门户需要你的账号登录、组织权限和实际租户版本。仓库不能替你创建或导出租户原生资产，也不能伪造“跨租户安装成功”证据。
3. 已经完成的是：本地可构建代码、导入工作表、JSON Schema、Java 8 插件核心、KWC 包、部署预检、C-only 交付组包和测试脚本。
4. 你必须完成的是：登录苍穹后确认版本，按工作表创建/导入平台模型，创建 KWC，编译薄插件，注册工具，导出产品包，在第二个干净环境安装并保存证据。

---

## 1. 本次新增和修复的代码

### 1.1 AI 调用治理

目录：`local/backend/src/main/java/com/xinji/foundation/ai/`

已经实现：

- 请求级动态总超时：`timeoutMs` 被限制在配置的最小值和最大值之间，并作为整个 Agent 调用的硬截止时间。
- 单次尝试超时：每次请求使用 `min(剩余总时间, perAttemptTimeoutMs)`。
- 分类重试：只重试网络错误、超时、协议错误和 HTTP 408/425/429/500/502/503/504。
- 退避策略：指数退避、随机抖动、最大退避，以及 Agent `Retry-After` 支持。
- 幂等恢复：完成请求直接重放；处理中请求返回 425 和 `Retry-After`；失败、过期或租约超时请求可用同一 key 恢复执行。
- 请求冲突保护：同一幂等 key 对应不同请求摘要时返回 `IDEMPOTENCY_CONFLICT`。
- 数据库限流：固定窗口计数存入 `ai_rate_limit_bucket`，多实例共享，不再依赖单机内存。
- 调用日志：记录调用状态、总耗时、尝试次数、总退避、HTTP 状态、摘要、错误码和回放关系。
- 重试明细：每一次尝试单独记录耗时、HTTP 状态、是否可重试、退避和脱敏错误。
- 指标：Micrometer 记录调用、尝试、重试和延迟指标。
- 服务账号鉴权：苍穹 Java 插件使用独立服务令牌，默认仅有 `ai:invoke`、`ai:log:read`、`module:read`。

数据库迁移：`local/backend/src/main/resources/db/migration/V2__ai_gateway_reliability.sql`

### 1.2 KWC 公共组件包

目录：`kingdee/kwc-common/`

构建产物：

- `dist/index.js`：统一入口。
- `dist/common-shell.js`：公共壳组件。
- `dist/api-client.js`：Bearer、requestId、幂等、动态超时、统一错误处理。
- `dist/host-adapter.js`：浏览器/本地适配。
- `dist/kingdee-host-adapter.js`：真实租户桥接适配。
- `dist/component-manifest.json`：组件元数据。
- `dist/checksums.sha256`：文件完整性清单。
- `deliverables/package/xinji-kwc-common-1.0.0.zip`：可上传/复制到平台组件工程的源码包。

KWC 不猜测平台全局变量。你需要在苍穹 KWC 运行时提供：

```javascript
window.__XINJI_KINGDEE_KWC_BRIDGE__ = {
  getLocale: () => 'zh-CN',
  getAccessToken: async () => token,
  getCurrentUser: async () => ({ id, username, displayName, roles, permissions }),
  openPage: (path) => {},
  showMessage: (level, message) => {},
  confirm: async (message) => true,
  fireEvent: (name, detail) => {}
};
```

只需把这 7 个方法映射到你实际 KWC 版本的宿主 API。业务组件不需要改。

### 1.3 苍穹 Java 插件

- 可独立验证的 Java 8 核心：`kingdee/java-plugin/src/main/java/com/xinji/kingdee/FoundationPluginCore.java`
- 苍穹薄包装模板：`kingdee/java-plugin/cosmic-template/.../XinjiFoundationFormPlugin.java.template`
- Java 8 自测：`kingdee/java-plugin/scripts/verify-java8.sh`

核心能力：

- 只允许访问 `/api/v1/ai/*`、`/api/v1/modules*`、`/api/v1/public/*`、`/actuator/health`。
- HTTPS/HTTP URL 校验，禁止 URL 用户信息、路径穿越和未授权路径。
- 连接超时、读取超时、最大响应体限制。
- 服务令牌、requestId、Idempotency-Key 自动传递。
- 错误正文脱敏，不输出 token、secret、password、authorization。

### 1.4 领域模型和 Agent 工具

源清单：

- `kingdee/domain-models/common-foundation-models.yaml`
- `kingdee/agent-tools/tool-registration.yaml`

生成文件：

- `kingdee/domain-models/generated/common-foundation-models.import.json`
- `kingdee/domain-models/generated/model-fields.import.csv`
- `kingdee/domain-models/generated/role-permissions.import.csv`
- `kingdee/agent-tools/generated/*.registration.json`
- `kingdee/generated-assets-manifest.json`

生成器只读取 `owner: C` 的资产。A/B 预留工具不会进入生成结果。

---

## 2. 本地使用步骤

### 2.1 准备环境变量

在项目根目录：

```bash
cp .env.example .env
```

至少修改：

```dotenv
POSTGRES_PASSWORD=一个强数据库密码
APP_DEMO_ADMIN_PASSWORD=一个强管理员密码
APP_SERVICE_TOKEN=至少32位随机字符串
```

生成服务令牌：

Linux/macOS：

```bash
openssl rand -base64 48 | tr -d '\n'
```

PowerShell：

```powershell
[Convert]::ToBase64String((1..48 | ForEach-Object { Get-Random -Maximum 256 }))
```

服务令牌不要提交 Git，不要粘贴到 KWC 前端代码，只放在后端部署环境和苍穹服务端密钥配置中。

### 2.2 启动本地全栈

```bash
docker compose up --build -d
```

检查：

```bash
docker compose ps
curl http://localhost:8080/actuator/health
```

前端：`http://localhost:8088`
后端：`http://localhost:8080`
Mock Agent：`http://localhost:8090`

注意：Compose 中还包含 A 的笔迹服务，这是原项目已有服务。C 的代码没有改动它；只验收 C 时可只启动：

```bash
docker compose up --build -d postgres mock-agent backend frontend
```

若现有 Compose 因 backend 对 handwriting-service 的 `depends_on` 仍拉起它，保持运行即可，不对其代码进行修改。

### 2.3 验证 AI 调用

先登录：

```bash
curl -s http://localhost:8080/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"student_demo","password":"demo123"}'
```

从返回值复制 `data.accessToken`：

```bash
export TOKEN='登录返回的令牌'
export IDEMPOTENCY_KEY="manual-$(date +%s)-0001"
```

调用：

```bash
curl -i http://localhost:8080/api/v1/ai/invoke \
  -H "Authorization: Bearer $TOKEN" \
  -H "Idempotency-Key: $IDEMPOTENCY_KEY" \
  -H 'Content-Type: application/json' \
  -d '{
    "moduleCode":"COMMON",
    "operation":"echo",
    "input":{"message":"C gateway test"},
    "timeoutMs":1000
  }'
```

用完全相同的 key 和正文再调用一次，返回的 `data.replayed` 应为 `true`。

查看调用日志：

```bash
curl -s http://localhost:8080/api/v1/ai/call-logs \
  -H "Authorization: Bearer $TOKEN"
```

复制 `callId` 后查看重试明细：

```bash
curl -s http://localhost:8080/api/v1/ai/call-logs/CALL_ID/attempts \
  -H "Authorization: Bearer $TOKEN"
```

### 2.4 验证苍穹服务令牌

```bash
export SERVICE_TOKEN='与 APP_SERVICE_TOKEN 相同的值'
curl -i http://localhost:8080/api/v1/ai/invoke \
  -H "Authorization: Bearer $SERVICE_TOKEN" \
  -H "Idempotency-Key: kingdee-service-test-0001" \
  -H 'Content-Type: application/json' \
  -d '{"moduleCode":"COMMON","operation":"echo","input":{"source":"kingdee"},"timeoutMs":1000}'
```

服务令牌访问 `/api/v1/audit-logs` 应返回 403。这是最小权限设计，不是故障。

### 2.5 执行本地验收

```bash
python3 tests/run_c_verification.py

# 在 Maven 可用的 CI/开发机上要求后端测试必须执行：
python3 tests/run_c_verification.py --require-backend
```

启动全栈后：

```bash
XINJI_SERVICE_TOKEN="$SERVICE_TOKEN" python3 tests/run_c_verification.py --live-e2e

# 正式验收时同时要求 Maven 和在线 E2E：
XINJI_SERVICE_TOKEN="$SERVICE_TOKEN" python3 tests/run_c_verification.py --require-backend --require-live-e2e
```

---

## 3. 登录苍穹开发环境后的第一轮信息采集

打开用户提供的开发环境地址并选择组织“软件杯小子”。登录后不要马上复制插件，先记录版本。

1. 找到“环境信息 / 关于 / 开发环境信息”一类入口。
2. 记录租户 ID、平台版本、构建号。
3. 打开 Java SDK 或二开工程下载入口，记录 SDK 版本和支持 JDK。
4. 打开 KWC 组件开发入口，记录 KWC 运行时版本、模块格式和发布方式。
5. 打开 Agent 开发平台，确认是否可创建自定义工具、工具鉴权类型和 Schema 版本。
6. 打开产品/应用发布入口，确认产品包导出格式和是否支持安装到第二租户。
7. 把结果填入：

```bash
cp kingdee/deployment/environment.template.yaml kingdee/deployment/environment.local.yaml
```

8. 执行：

```bash
python3 kingdee/deployment/preflight.py kingdee/deployment/environment.local.yaml
```

在所有 `FILL_*` 被替换前，不进入正式部署。

---

## 4. 创建 C 的公共领域模型

不同版本菜单名称可能是“开发服务云 / 动态领域模型 / 业务对象 / 低代码开发”。以你登录后看到的实际名称为准。

### 4.1 导入前准备

运行：

```bash
python3 kingdee/tools/build_c_assets.py
```

打开：

- `kingdee/domain-models/generated/model-fields.import.csv`
- `kingdee/domain-models/generated/role-permissions.import.csv`
- `kingdee/domain-models/generated/common-foundation-models.import.json`

### 4.2 建模顺序

只创建下列 C 模型：

1. `xj_user`
2. `xj_common_task`
3. `xj_file_object`
4. `xj_audit_log`
5. `xj_idempotency_record`
6. `xj_ai_call_log`
7. `xj_ai_call_attempt_log`
8. `xj_ai_rate_limit_bucket`
9. `xj_module_registration`

每个模型：

1. 新建业务对象/领域模型。
2. 编码必须与清单 `code` 完全一致。
3. 根据 CSV 添加字段；文本长度、必填、唯一、枚举值必须一致。
4. 添加索引；尤其：
   - 幂等：`scope + idempotency_key` 唯一。
   - 重试日志：`call_id + attempt_no` 唯一。
   - 限流：`scope + window_start` 唯一。
5. 对 `version` 开启乐观锁；如果平台使用自己的版本字段，记录映射而不是重复创建。
6. `xj_audit_log`、`xj_idempotency_record`、`xj_ai_rate_limit_bucket` 禁止业务用户编辑。
7. 原始 Prompt、输入正文、令牌不得新增为字段。
8. 发布模型并保存发布日志。

### 4.3 角色和数据权限

创建或映射：

- `XJ_STUDENT`
- `XJ_COUNSELOR`
- `XJ_ADMIN`
- `XJ_INTEGRATION_SERVICE`

按 `role-permissions.import.csv` 配置。重点验证：

1. 学生只能查看自己的任务、文件和 AI 日志。
2. 咨询师只能查看授权学生或自己的数据。
3. 管理员可查看全部审计和 AI 日志。
4. 集成服务账号不能读取审计、用户资料或文件正文。

用四个不同测试账号登录验证，不要只看设计器配置。

### 4.4 创建服务模型/API

1. 在平台中创建“外部服务 / 服务模型 / REST 服务”一类资产。
2. 以 `contracts/openapi.yaml` 为契约。
3. 基础地址填你部署的 C 网关 HTTPS 地址。
4. 鉴权使用服务端密钥，不允许前端明文保存 `APP_SERVICE_TOKEN`。
5. 对写操作映射 `Idempotency-Key`。
6. 传递或生成 `X-Request-Id`。
7. 将 409/425/429/502/504 映射为平台可识别的失败状态。
8. 对 429 读取 `Retry-After`，不要在平台无限立即重试。

---

## 5. KWC 公共组件部署

### 5.1 构建

```bash
npm --prefix kingdee/kwc-common run package
```

产物：`deliverables/package/xinji-kwc-common-1.0.0.zip`

### 5.2 在平台创建组件

1. 打开 KWC/自定义组件管理。
2. 新建组件，编码建议 `xj_kwc_common`。
3. 模块格式选 ESM；入口为 `index.js`。
4. 上传 zip 或把 `dist/` 内容复制到平台生成的组件工程。
5. 按 `component-manifest.json` 配置属性、事件和入口。
6. 添加 `theme.css`。
7. 发布到测试版本，不直接发布生产版本。

### 5.3 实现真实 Host Bridge

在平台组件的启动文件中，根据你的 KWC SDK 实际 API 实现 7 个方法。建议单独建 `kingdee-bridge.js`，不要修改 `dist/kingdee-host-adapter.js`。

示例骨架：

```javascript
window.__XINJI_KINGDEE_KWC_BRIDGE__ = {
  getLocale() {
    return PLATFORM_API_GET_LOCALE() || 'zh-CN';
  },
  async getAccessToken() {
    return PLATFORM_API_GET_SHORT_LIVED_USER_TOKEN();
  },
  async getCurrentUser() {
    const user = await PLATFORM_API_GET_CURRENT_USER();
    return {
      id: String(user.id),
      username: String(user.username),
      displayName: String(user.name || user.username),
      roles: user.roles || [],
      permissions: user.permissions || [],
      organizationId: user.organizationId ? String(user.organizationId) : undefined
    };
  },
  openPage(path) {
    PLATFORM_API_OPEN_PAGE(path);
  },
  showMessage(level, message) {
    PLATFORM_API_SHOW_MESSAGE(level, message);
  },
  async confirm(message) {
    return Boolean(await PLATFORM_API_CONFIRM(message));
  },
  fireEvent(name, detail) {
    PLATFORM_API_FIRE_CUSTOM_EVENT(name, detail);
  }
};
```

将 `PLATFORM_API_*` 替换成你租户 SDK 的真实方法。只有这个桥接文件允许因版本不同而调整。

### 5.4 KWC 验收

1. 页面加载后公共壳正常渲染，且只渲染一次当前挂载实例。
2. 显示当前用户、模块编码和运行状态。
3. 调用 `/api/v1/public/info` 成功。
4. 使用用户短期令牌调用 `/api/v1/me` 成功。
5. 触发一次 `xinjiGatewayResult` 或组件自定义事件。
6. 卸载页面后不会继续发请求或保留事件监听器。
7. 浏览器控制台和平台日志中没有服务令牌。

---

## 6. Java 插件接入

### 6.1 确认 SDK

官方 SDK 中存在 `kd.bos.form.plugin.AbstractFormPlugin`；不同版本的 `CustomEventArgs` 取值方法可能不同，因此只在薄包装层适配。

### 6.2 复制代码

1. 在苍穹开发工具生成一个最小“表单插件”工程。
2. 确认工程使用 JDK 8 或环境要求的版本。
3. 将 `FoundationPluginCore.java` 复制到工程：

```text
src/main/java/com/xinji/kingdee/FoundationPluginCore.java
```

4. 将模板复制并去掉 `.template` 后缀：

```text
kingdee/java-plugin/cosmic-template/src/main/java/com/xinji/kingdee/cosmic/XinjiFoundationFormPlugin.java.template
→ 你的工程/src/main/java/com/xinji/kingdee/cosmic/XinjiFoundationFormPlugin.java
```

### 6.3 映射事件参数

先尝试直接编译。若错误集中在 `CustomEventArgs` 取值：

1. 在 IDE 跳转到你 SDK 的 `CustomEventArgs`。
2. 找到“事件名”和“事件参数”对应 getter。
3. 只修改：
   - `readEventName`
   - `readEventPayload`
4. 不改 `FoundationPluginCore`。

### 6.4 配置密钥

在平台 Java 插件运行环境或密钥管理中配置：

```text
xinji.gateway.base-url=https://你的网关地址/
xinji.gateway.service-token=与 APP_SERVICE_TOKEN 一致的密钥引用
```

模板也支持环境变量：

```text
XINJI_GATEWAY_BASE_URL
XINJI_GATEWAY_SERVICE_TOKEN
```

不要把实际值写进 Java 文件、Gradle 文件、日志或产品包说明。

### 6.5 绑定和验证

1. 将插件绑定到一个 C 的公共测试表单。
2. 从前端触发自定义事件 `xinji.health`。
3. 页面应收到 `xinjiGatewayResult`，内容包含健康状态。
4. 触发 `xinji.ai.invoke`，参数必须是符合 `AiInvokeRequest` 的 JSON。
5. 在后端 `ai_call_log` 和 `audit_log` 中找到同一个 requestId。
6. 用服务账号尝试读取审计接口，必须被拒绝。
7. 在平台日志中搜索 token 的前 6 位，必须无结果。

---

## 7. Agent 工具注册

### 7.1 生成注册文件

```bash
python3 kingdee/tools/build_c_assets.py
```

只注册：

- `common_ai_invoke`
- `common_create_task`
- `common_get_file_metadata`

不要注册或实现 A/B 的预留工具。

### 7.2 平台操作

在 Agent 开发平台的“工具 / API 工具 / MCP 或服务工具”入口：

1. 新建工具。
2. 名称与 `*.registration.json` 的 `name` 完全一致。
3. 描述使用 `description`。
4. 输入 Schema 粘贴 `inputSchema`。
5. HTTP 方法和路径使用 `method`、`path`。
6. 鉴权绑定平台服务账号或服务模型，密钥不可见给模型。
7. `common_ai_invoke` 必须生成 8～120 位幂等 key。
8. 配置最大执行时间不得高于网关 `APP_AGENT_TIMEOUT_MS`。
9. 对 429 按 `Retry-After` 延后；平台自动重试次数建议不超过 1，避免与网关内部重试叠加。
10. 保存并发布测试版本。

### 7.3 工具验收

为每个工具保存：

- 输入 JSON。
- 平台运行轨迹。
- HTTP 状态和 requestId。
- 后端审计记录。
- 失败用例。

`common_ai_invoke` 至少验证：成功、同 key 回放、同 key 不同正文冲突、动态超时、429、不可重试 400。

---

## 8. 产品包、部署和跨租户验收

### 8.1 生成 C-only 工程交付包

```bash
python3 kingdee/deployment/build_c_delivery.py
```

输出：

```text
deliverables/package/xinji-c-delivery-1.1.0.zip
```

这个 zip 是带 SHA-256 清单的 C 工程交付包，不冒充苍穹原生产品包。

### 8.2 导出平台原生产品包

在苍穹“应用发布 / 产品管理 / 导出安装包”入口：

1. 新建或选择“心迹AI”产品。
2. 只勾选 C 的 9 个公共模型、角色权限、服务模型、KWC 公共组件、Java 插件和 3 个 C 工具。
3. 不勾选 A/B 尚未完成或由他人维护的业务资产。
4. 执行依赖检查。
5. 发布测试版本 `1.1.0`。
6. 导出平台原生安装包。
7. 将文件放入 `kingdee/deployment/tenant-native-assets/`。
8. 在 `environment.local.yaml` 填写真实文件路径。
9. 执行：

```bash
python3 kingdee/deployment/preflight.py \
  kingdee/deployment/environment.local.yaml \
  --require-native-export
```

### 8.3 将原生包加入交付包

```bash
python3 kingdee/deployment/build_c_delivery.py \
  --environment kingdee/deployment/environment.local.yaml \
  --include-native-export
```

### 8.4 干净租户安装

必须使用第二个无心迹资产的测试租户：

1. 安装产品包。
2. 检查依赖错误；禁止在目标租户手工补资产后冒充“一键安装成功”。
3. 给四类测试账号分配角色。
4. 配置网关 HTTPS 地址和服务令牌引用。
5. 打开公共页面和 KWC。
6. 执行 Java 插件健康检查。
7. 调用 3 个 Agent 工具。
8. 执行权限矩阵和 E2E。
9. 填写 `cleanTenantInstallVerified: true`。
10. 保存安装日志、版本号和截图索引到 `kingdee/evidence/`。

### 8.5 回滚演练

1. 保留上一版原生产品包和网关镜像标签。
2. 备份数据库。
3. 安装 1.1.0 并完成一次调用。
4. 回滚平台产品包和网关镜像。
5. 验证旧版页面、任务、文件和日志可读。
6. 轮换服务令牌。
7. 保存回滚耗时和结果。

---

## 9. 最终验收清单

### 代码验收

- [ ] `mvn -f local/backend/pom.xml test` 全部通过。
- [ ] `npm --prefix kingdee/kwc-common run package` 通过。
- [ ] `bash kingdee/java-plugin/scripts/verify-java8.sh` 通过。
- [ ] `python3 tests/run_c_verification.py --require-backend` 通过。
- [ ] `python3 tests/run_c_verification.py --require-backend --require-live-e2e` 在运行环境通过。

### AI 治理验收

- [ ] 动态总超时生效。
- [ ] 可重试错误按规则重试。
- [ ] 400 等不可重试错误只调用一次。
- [ ] 失败幂等记录可恢复。
- [ ] 完成幂等记录可回放。
- [ ] 同 key 不同正文返回冲突。
- [ ] 多实例共用数据库限流。
- [ ] 429 有 `Retry-After` 和 `X-RateLimit-Limit`。
- [ ] 每次尝试都有脱敏日志。

### 苍穹验收

- [ ] 9 个 C 模型已发布。
- [ ] 四类角色权限实测通过。
- [ ] KWC 真实 Host Bridge 的 7 个方法已映射。
- [ ] Java 插件使用实际 SDK 编译和发布。
- [ ] 3 个 C 工具已注册并运行。
- [ ] 平台原生产品包已导出。
- [ ] 第二干净租户一键安装通过。
- [ ] 回滚演练通过。
- [ ] 证据中无令牌、Cookie、个人敏感数据。

---

## 10. 常见失败处理

### 语雀 403

用已登录浏览器打开并将与 KWC/插件/产品包相关的页面导出为 PDF 或 Markdown，再与本手册核对。不要把账号 Cookie 发给他人或提交仓库。

### Java 插件编译找不到类

说明租户 SDK 版本或工程依赖未确认。以开发工具生成的插件工程为基准，只复制核心类和模板；不要在独立 Maven 工程中猜 SDK 坐标。

### KWC 找不到宿主方法

只修改 `kingdee-bridge.js` 的 7 个映射，不修改公共组件包。把实际 SDK 名称和版本填写进环境基线。

### 429 很多

检查平台外层是否又配置了多次立即重试。网关已经内部重试，平台只应尊重 `Retry-After`，避免重试放大。

### 同一幂等 key 一直 425

查看响应 `Retry-After`。若原调用进程崩溃，等待租约过期后同 key 会自动恢复；不要改变请求正文。

### 无法声明“全部完成”

只有当平台原生包已导出、第二租户安装、E2E 和回滚证据齐全后，才能把“苍穹集成与部署”标成完成。本地代码和设计文件完成不等于租户部署完成。
