# 角色B 进度总结

**成员**: 角色B — 多模态算法与Agent工程  
**主责**: 房树人/沙盘与Agent  
**更新日期**: 2024-07-16

---

## 一、总体进度

```
████████████████████░░░░░░░░  ≈ 60%

已完成: ~42 / 70 任务
待完成: ~28 任务（其中 6 项阻塞于苍穹 KWC SDK，6 项阻塞于 Spring Boot 环境）
```

| 模块 | 进度 | 状态 |
|------|------|------|
| 接口契约 (OpenAPI / Schema / 错误码 / 映射) | 100% | ✅ |
| 平台适配器 (PlatformAdapter + Mock + 测试) | 100% | ✅ |
| 沙盘数据 (字典 / 图标 / 样本 / 生成器) | 100% | ✅ |
| 沙盘 KWC 画布 (Canvas 原型) | 100% | ✅ |
| 沙盘 Java 领域 (几何特征 / DBSCAN / 测试) | 100% | ✅ |
| 房树人 Java 领域 (视觉观察 / 降级 / 测试) | 60% | ⏳ KWC 组件待 SDK |
| Agent Prompt (沙盘 / 房树人 v1.0) | 100% | ✅ |
| RAG 知识库 (沙盘 / 房树人方法论) | 40% | ⏳ 需扩至 5+ 篇/域 |
| Agent 工具 Schema (3 工具) | 100% | ✅ |
| Agent 任务流 (沙盘 / 房树人) | 100% | ✅ |
| API 控制器 (Sandplay / HTP Controller) | 80% | ⏳ 错误处理/日志/契约测试待 Spring Boot |
| 结果展示 KWC 组件 | 0% | 🔒 阻塞于苍穹 KWC SDK |
| 内容安全 (诊断过滤 / PII / 危机检测) | 70% | ⏳ 单元测试待补充 |
| AI 评测 / 安全测试 | 50% | ⏳ 房树人评测集、执行器待补充 |
| Mock 数据与联调 | 30% | ⏳ HTP mock 数据、端到端验证待 Spring Boot |
| 文档与苍穹迁移准备 | 60% | ⏳ 迁移检查清单已完成，技术文档待完善 |

---

## 二、已交付资产清单

### 2.1 接口契约 (contracts/)

| 文件 | 说明 |
|------|------|
| `contracts/openapi/sandplay-analysis.yaml` | 沙盘分析 API，OpenAPI 3.0，含请求/响应 Schema、幂等设计、示例 |
| `contracts/openapi/htp-analysis.yaml` | 房树人分析 API，含多模态降级响应设计 |
| `contracts/schemas/sandplay-element.schema.json` | 沙盘元素 JSON Schema（7 字段约束） |
| `contracts/schemas/htp-questionnaire.schema.json` | 房树人问卷 JSON Schema（必填/可选字段、枚举约束） |
| `contracts/schemas/agent-output.schema.json` | Agent 输出统一 Schema（沙盘/HTP 差异字段分离） |
| `contracts/errors/multimodal-error-codes.yaml` | 17 个统一错误码（SANDBOX_*/HTP_*/MULTIMODAL_*/AGENT_*），含 HTTP 状态码和用户操作指引 |
| `contracts/mappings/sandplay-field-mapping.csv` | 沙盘四列映射表（概念字段 → 苍穹字段 → DB字段 → API字段） |
| `contracts/mappings/htp-field-mapping.csv` | 房树人的四列映射表 |

### 2.2 Java 领域服务 (local/java-domain/)

| 文件 | 说明 |
|------|------|
| `pom.xml` | Maven 项目配置（Java 17 + JUnit 5 + Jackson） |
| `platform/PlatformAdapter.java` | 平台适配器接口（Agent分析/多模态/RAG/工具/审计 5 个方法族） |
| `platform/LocalMockAdapter.java` | 本地 Mock 实现（幂等/降级/RAG 检索/审计日志） |
| `platform/PlatformAdapterFactory.java` | 适配器工厂（通过 `app.platform.mode` 切换） |
| `platform/AgentException.java` | Agent 调用异常 |
| `platform/MultimodalException.java` | 多模态模型异常 |
| `platform/ToolExecutionException.java` | 工具执行异常 |
| `sandplay/SandplayGeometryService.java` | 几何特征提取（类别分布/象限分析/DBSCAN 聚类/邻接矩阵/坐标校验） |
| `htp/HTPObservationService.java` | 视觉观察服务（多模态调用 + 超时/不可用降级） |
| `safety/ContentFilterService.java` | 内容安全过滤（14+ 诊断术语替换/PII 模式检测/15+ 危机关键词） |
| `controller/SandplayAnalysisController.java` | 沙盘分析控制器（安全预检 → 特征提取 → Agent → 过滤 → 响应） |
| `controller/HTPAnalysisController.java` | 房树人分析控制器（含多模态降级分支） |
| `data/SandplayLayoutGenerator.java` | 沙盘布局随机生成器（4 种分布模式） |
| `model/*.java` | 9 个 DTO 模型类 |

**单元测试**:
- `PlatformAdapterTest.java` — 16 个测试用例（沙盘/HTP/RAG/工具/工厂）
- `SandplayGeometryServiceTest.java` — 15+ 个测试用例（校验/分布/象限/DBSCAN/邻接/距离）
- `HTPObservationServiceTest.java` — 5 个测试用例（观察/降级/字段完整性）

### 2.3 AI 资产 (ai/)

| 文件 | 说明 |
|------|------|
| `prompts/sandplay-analysis-agent-v1.md` | 沙盘分析 Agent System Prompt v1.0（五段式: 角色/知识边界/输出 Schema/安全约束/Few-shot × 2） |
| `prompts/htp-analysis-agent-v1.md` | 房树人分析 Agent System Prompt v1.0（五段式 + 观察与推测分离 + 降级示例） |
| `tools/save_sandbox_record.schema.json` | 保存沙盘记录工具（含权限/幂等/超时 5s/重试 3 次/错误回退文案） |
| `tools/save_htp_record.schema.json` | 保存房树人记录工具 |
| `tools/get_rag_context.schema.json` | RAG 检索工具（主题过滤/风险标签过滤/超时 3s） |
| `workflows/sandplay-analysis-workflow.yaml` | 沙盘分析任务流（7 步: 验证 → 特征 → RAG → Agent → 安全 → 保存 → 审计） |
| `workflows/htp-analysis-workflow.yaml` | 房树人分析任务流（含多模态可用性判断 → 降级分支 → Agent → 安全 → 保存） |
| `knowledge-base/sandplay-methodology/sand-ref-001-sandplay-basics.md` | 沙盘基础方法论文档（含完整元数据/边界声明/文化敏感度/引用建议） |
| `knowledge-base/htp-methodology/htp-ref-001-htp-overview.md` | 房树人方法论概述（含学术争议说明/使用边界/中国大学生文化因素） |
| `eval/sandplay-eval-set.json` | 沙盘评测集（10 条: 正常 × 5 + 边界 × 2 + 攻击 × 2 + 危机 × 1） |
| `safety/safety-test-cases.json` | 安全测试集（15 条: 诊断拒答/提示注入/越界医疗/自伤/PII/正常/情绪困扰） |

### 2.4 数据资产 (data/)

- `dictionaries/sandplay-elements.json` — 35 个沙盘元素（7 类别），含标签和分类元数据
- `mock/sandplay-samples.json` — 12 个沙盘布局样本（覆盖稀疏/密集/聚类/对称/边界/空画布/校园/抽象等场景）

### 2.5 KWC 前端原型 (local/frontend-prototype/)

- `sandplay-canvas.html` — 完整沙盘 Canvas 原型（元素库面板/分类筛选/拖拽添加/选中移动/撤销重做/网格/序列化/API 调用 mock）
- `assets/sandplay/*.svg` — 36 个元素图标（按类别着色）

### 2.6 工程配置

- `.gitignore` — 忽略 `openspec/` 和 `.claude/` 目录
- `kingdee/evidence/sandplay-htp-migration-checklist.md` — 苍穹迁移检查清单（8 大类: 领域模型/KWC/Java 插件/Agent 注册/工具注册/RAG/权限/首日验证）

---

## 三、架构关键决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 平台隔离 | **PlatformAdapter 接口 + LocalMockAdapter / KingdeeAdapter** | 苍穹环境不可用时，Mock 独立跑通全链路；到位后仅切换配置 |
| 几何算法 | **纯 Java 手写**（DBSCAN、欧几里得距离、象限划分） | 不依赖 PostGIS 等扩展，保证苍穹兼容性；元素量 < 100，O(n²) 可接受 |
| Agent 架构 | **单 Agent 明确任务**（非多 Agent 自主对话） | 分析链路确定，可控性和可审计性优先 |
| Prompt 结构 | **五段式**（角色 → 知识边界 → 输出 Schema → 安全约束 → Few-shot） | 结构一致，评测可对比；苍穹 Agent 平台原生支持 |
| 多模态降级 | **模型不可用时自动继续**（仅问卷分析） | 不阻塞主链路，用户体验友好 |
| 沙盘 MVP | **结构化坐标采集**（不依赖图像识别） | 几何提取可靠、可测试、可解释 |
| 房树人路线 | **轻量方案**（上传 + 问卷 + 多模态 API，不做 DL 训练） | 符合 P1 定位，降低开发风险和模型合规风险 |

---

## 四、待完成任务

### 🔒 阻塞于苍穹 KWC SDK

| 任务 | 说明 |
|------|------|
| 6.1 房树人图片上传 KWC 组件 | 依赖 KWC 文件上传 API |
| 6.2 房树人结构化问卷 KWC 组件 | 依赖 KWC 表单组件 |
| 6.4 房树人提交页面 | 依赖 KWC 页面布局 |
| 10.1 沙盘结果展示 KWC 组件 | 几何统计面板 + Agent 分析面板 |
| 10.2 房树人结果展示 KWC 组件 | Tab 切换（画作/问卷/AI/说明） |
| 10.3 结果加载/错误/空状态 UI | 依赖 KWC 生命周期 |

### 🔒 阻塞于 Spring Boot 环境

| 任务 | 说明 |
|------|------|
| 9.3 统一错误处理 (ControllerAdvice) | 依赖 Spring Web |
| 9.4 请求/响应日志 | 依赖 Spring AOP / Filter |
| 9.5 API 契约测试 | 依赖 MockMvc / REST Assured |
| 13.4 沙盘端到端集成验证 | 依赖完整链路运行 |
| 13.5 房树人端到端集成验证 | 同上 |

### ⏳ 补充完善（不阻塞）

| 任务 | 说明 |
|------|------|
| 7.3/7.4 RAG 语料扩至 5+ 篇/域 | 当前各 1 篇基础文档 |
| 12.2 房树人评测集 | 结构已定义，具体用例待补充 |
| 12.4 评测执行器测试 | 待编写自动评分逻辑 |
| 12.5 安全拒绝测试 | 待基于 safety-test-cases.json 编写 |
| 11.5 ContentFilterService 单元测试 | 待补充诊断替换/PII 脱敏/危机检测的自动化验证 |
| 13.1/13.2 HTP Mock 数据生成器 + 样本 | 沙盘已有，房树人待补充 |
| 14.1-14.5 技术文档 | 架构和接口已在 design.md 中描述，需整理为交付格式 |

---

## 五、与角色 C 的接口依赖

角色 B 向 C 已提供：

- [x] 沙盘分析 OpenAPI 契约 → C 据此实现统一网关路由
- [x] 房树人分析 OpenAPI 契约 → C 据此实现统一网关路由
- [x] 沙盘/房树人 DTO 模型 → C 纳入公共 DTO 规范
- [x] 统一错误码 → C 纳入全局错误处理
- [x] 字段映射表 → C 据此设计 PostgreSQL DDL
- [x] Agent 工具注册清单 → C 在苍穹 Agent 平台注册
- [x] 迁移检查清单 → C 协助苍穹环境部署

角色 B 等待 C 提供：

- [ ] KWC 公共组件规范（用于组件注册和生命周期管理）
- [ ] 统一网关接口（用于 API 鉴权/限流/路由）
- [ ] 文件上传能力（用于房树人图片上传）
- [ ] AI 调用超时/重试/幂等基础框架
- [ ] Mock Agent 环境（用于本地联调）

---

## 六、下一步行动

**优先级排序**（按阻塞情况）:

1. **立即可做**: RAG 语料扩充、房树人评测集补充、ContentFilterService 单元测试、HTP Mock 数据
2. **Spring Boot 环境就绪后**: 全局错误处理、请求日志、API 契约测试、端到端集成验证
3. **苍穹 KWC SDK 到位后**: 第 1 天 KWC Canvas 兼容性验证 → 迁移沙盘画布 → 实现结果展示组件 → 实现房树人 KWC 组件
4. **苍穹 Agent 平台到位后**: 注册 Agent → 注册工具 → 导入 RAG → 实现 KingdeeAdapter → 端到端验证
