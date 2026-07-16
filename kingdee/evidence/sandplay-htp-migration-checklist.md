# 沙盘/房树人 — 苍穹迁移检查清单

角色B维护 | 版本 1.0.0 | 2024-07-16

环境未到位时先在本地完成开发和验证，苍穹环境到位后按此清单逐项迁移。

---

## 一、领域模型映射

| 本地概念模型 | 苍穹领域模型 | 待迁移字段数 | 状态 |
|-------------|-------------|------------|------|
| SandplayElement | sandbox_record + sandbox_element 明细 | 16 | 待苍穹环境 |
| HTPAnalysisRequest | htp_record | 15 | 待苍穹环境 |
| Agent分析结果 | ai_analysis_report | 10+ | 待苍穹环境 |
| 审计记录 | agent_run + tool_call_record | 12 | 待苍穹环境 |

参考: [contracts/mappings/sandplay-field-mapping.csv](../../contracts/mappings/sandplay-field-mapping.csv), [htp-field-mapping.csv](../../contracts/mappings/htp-field-mapping.csv)

## 二、KWC组件注册

| 本地原型 | KWC组件名 | 依赖的KWC API | 状态 |
|---------|----------|-------------|------|
| [sandplay-canvas.html](../../local/frontend-prototype/sandplay-canvas.html) | SandplayCanvas | Canvas 2D, Drag & Drop | 待KWC SDK |
| 沙盘结果展示 | SandplayResultCard | 图表渲染, Tab切换 | 待KWC SDK |
| 房树人上传+问卷 | HTPUploadForm | 文件上传, 表单验证 | 待KWC SDK |
| 房树人结果展示 | HTPResultTabs | Tab切换, 图片预览 | 待KWC SDK |

> **首日验证**: KWC是否支持Canvas 2D API？如不支持，降级为DOM绝对定位。

## 三、Java插件/服务

| 本地Java类 | 苍穹部署方式 | 依赖的苍穹SDK | 状态 |
|-----------|------------|-------------|------|
| SandplayGeometryService | Java插件（纯POJO） | 无 | 可直接部署 |
| HTPObservationService | Java插件 + PlatformAdapter实现 | 多模态模型API | 待苍穹环境 |
| ContentFilterService | Java插件（纯POJO） | 无 | 可直接部署 |
| PlatformAdapter (KingdeeAdapter) | 服务模型 | Agent平台SDK | 待苍穹环境 |
| SandplayAnalysisController | 服务模型 | 苍穹Web服务 | 待苍穹环境 |
| HTPAnalysisController | 服务模型 | 苍穹Web服务 | 待苍穹环境 |

## 四、Agent注册

| Agent | Prompt文件 | 工具列表 | RAG知识库 | 模型需求 | 状态 |
|-------|-----------|---------|----------|---------|------|
| sandplay-analysis-agent | [ai/prompts/sandplay-analysis-agent-v1.md](../../ai/prompts/sandplay-analysis-agent-v1.md) | save_sandbox_record, get_rag_context | sandplay-methodology | 文本生成 | 待苍穹Agent平台 |
| htp-analysis-agent | [ai/prompts/htp-analysis-agent-v1.md](../../ai/prompts/htp-analysis-agent-v1.md) | save_htp_record, get_rag_context, multimodal_describe_image | htp-methodology | 文本生成 + 多模态(可选) | 待苍穹Agent平台 |

## 五、工具注册

| 工具名 | Schema文件 | 类型 | 权限级别 | 状态 |
|-------|-----------|-----|---------|------|
| save_sandbox_record | [ai/tools/save_sandbox_record.schema.json](../../ai/tools/save_sandbox_record.schema.json) | 写 | own-records | 待苍穹Agent平台 |
| save_htp_record | [ai/tools/save_htp_record.schema.json](../../ai/tools/save_htp_record.schema.json) | 写 | own-records | 待苍穹Agent平台 |
| get_rag_context | [ai/tools/get_rag_context.schema.json](../../ai/tools/get_rag_context.schema.json) | 读 | public-knowledge-base | 待苍穹Agent平台 |

## 六、RAG知识库

| 知识域 | 文档数 | 元数据状态 | 索引需求 | 状态 |
|-------|-------|----------|---------|------|
| sandplay-methodology | 1 (需扩至5+) | 完整 | 向量索引 | 待苍穹环境 |
| htp-methodology | 1 (需扩至5+) | 完整 | 向量索引 | 待苍穹环境 |

## 七、权限配置

| 角色 | 沙盘访问 | 房树人访问 | 分析结果 | 审计日志 |
|-----|---------|----------|---------|---------|
| 学生 | 自己的记录 | 自己的记录 | 自己的结果 | 不可见 |
| 咨询师 | 被分配工单关联的记录 | 同左 | 关联结果 | 可见相关操作 |
| 管理员 | 不可见（聚合除外） | 不可见（聚合除外） | 不可见 | 可见 |
| 系统管理员 | 不可见 | 不可见 | 不可见 | 可见 |

## 八、首日环境验证清单

- [ ] 确认苍穹平台版本和可用模型列表
- [ ] 创建最小领域模型（sandbox_record）并保存成功
- [ ] KWC是否支持Canvas 2D API？（如不支持则降级为DOM方案）
- [ ] 部署一个最小Java插件（返回固定JSON）并查看日志
- [ ] 创建一个最小Agent（RAG检索验证）
- [ ] Agent工具注册流程验证
- [ ] 确认文件上传能力和存储限制

---

> **文档状态**: 待苍穹环境到位后逐项验证。禁止在环境未就绪前凭猜测填写SDK版本。
