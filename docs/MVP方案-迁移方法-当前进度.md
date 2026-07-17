# 心迹AI — MVP方案 / 迁移方法 / 当前进度

角色B | 2024-07-16

---

## 一、MVP 方案

### 1.1 MVP 目标

```
┌──────────────────────────────────────────────────────────┐
│                    心迹AI MVP                             │
│                                                          │
│  ┌─────────────────┐      ┌─────────────────┐            │
│  │   沙盘界面       │      │   笔迹检测界面    │            │
│  │  ─────────────  │      │  ─────────────  │            │
│  │  Canvas 拖拽画布 │      │  Canvas 手写采集 │            │
│  │  元素库 + 特征   │      │  轨迹 + 特征     │            │
│  │        │         │      │        │         │            │
│  │   ┌────┴────┐   │      │   ┌────┴────┐   │            │
│  │   │🤖 AI助手 │   │      │   │🤖 AI助手 │   │            │
│  │   │(苍穹嵌入  │   │      │   │(苍穹嵌入  │   │            │
│  │   │ 式控件)   │   │      │   │ 式控件)   │   │            │
│  │   └─────────┘   │      │   └─────────┘   │            │
│  └─────────────────┘      └─────────────────┘            │
│                                                          │
│  共用: 苍穹嵌入式控件 AI 对话面板                           │
│  每个界面的知识库跟随页面内容自动切换                         │
└──────────────────────────────────────────────────────────┘
```

### 1.2 MVP 功能范围

**沙盘模块**（角色B负责）

| 功能 | 说明 |
|------|------|
| 元素库面板 | 35个元素，7类别，拖拽添加 |
| Canvas 画布 | 拖放/移动/选中/撤销重做/网格/清空 |
| 文字描述 | 500字以内 |
| 保存分析 | 序列化布局 → 几何特征提取 → Agent分析 |
| 嵌入智能体 | 对话面板，知识库跟随沙盘内容 |

**笔迹检测模块**（角色A负责，角色B提供Agent）

| 功能 | 说明 |
|------|------|
| Canvas 手写 | 自由绘制，采集坐标/速度/压力/停顿 |
| 实时特征 | 笔划数/书写速度/停顿次数/压力曲线 |
| 嵌入智能体 | 对话面板，知识库跟随笔迹内容 |

**AI 智能体**（角色B负责）

| 功能 | 说明 |
|------|------|
| 沙盘分析 Agent | Prompt v1.0 + RAG 沙盘知识库 |
| 笔迹分析 Agent | Prompt + RAG 笔迹知识库 |
| 苍穹嵌入式控件 | Java 插件调 EmbeddedControlService |

### 1.3 智能体嵌入方式

基于金蝶苍穹文档，嵌入方式：

```
表单设计器
  ├── 拖一个自定义控件，绑定方案 ai-embedding-ctrl
  ├── 设置展示位置（下 > 上 > 右 > 左 > 中间）
  │
  └── Java插件中:
       1. 重写 chat 事件 → 接收用户输入
       2. 读取页面字段 → 构造Agent上下文
       3. 调用 EmbeddedControlService.show() → 弹出对话窗
       4. 调用 EmbeddedControlService.chat() → 发送消息
       5. Agent结果 → 回填到页面字段
```

**三种展示样式**：悬浮右侧 / 嵌入页面容器 / 小弹窗

**关键参数**：
- `assistantId` 或 `agents[]`：绑定智能体
- `showStyle.showKey`：展示位置锚点
- `mountingMethod`：嵌入方式
- `fastQuestion`：打开即问

---

## 二、迁移方法

### 2.1 核心原则：PlatformAdapter 双轨

```
                ┌──────────────────┐
  Controller ──►│  PlatformAdapter │  ← 接口永远不变
                │   (interface)    │
                ├────────┬─────────┤
                │ Local  │ Kingdee │
                │ Mock   │ Adapter │
                └────────┴─────────┘
                 现在可跑   苍穹到位后实现

迁移工作量 = 写一个 KingdeeAdapter 类
业务代码（Controller/Service）一行不改
```

### 2.2 各类资产的迁移操作

```
┌────────────────┬──────────────────────────────────────────┐
│ 本地资产        │ 苍穹平台操作                               │
├────────────────┼──────────────────────────────────────────┤
│                │                                          │
│ contracts/     │ → 表单设计器: 对照 OpenAPI 创建字段        │
│ openapi/*.yaml │   领域建模: 对照 mappings/*.csv 建实体     │
│ mappings/*.csv │                                          │
│                │                                          │
│ local/         │ → mvn package 编译 jar                   │
│ java-domain/   │ → 苍穹开发者中心 → Java插件管理 → 上传jar  │
│ *.java         │   配置服务模型 → 暴露为REST API            │
│                │                                          │
│ local/         │ → 苍穹 KWC 组件编辑器                     │
│ frontend-      │   把 HTML/JS/CSS 粘贴进去                 │
│ prototype/     │   适配 KWC 生命周期钩子                    │
│ *.html         │   注册到页面上                             │
│                │                                          │
│ ai/prompts/    │ → 苍穹 Agent 平台 → 创建Agent             │
│ *.md           │   粘贴 System Prompt                      │
│                │   配置模型/参数                            │
│                │                                          │
│ ai/tools/      │ → 苍穹 Agent 平台 → 工具管理              │
│ *.schema.json  │   注册工具 → 粘贴 JSON Schema             │
│                │   绑定到 Java 插件服务                     │
│                │                                          │
│ ai/knowledge-  │ → 苍穹 Agent 平台 → 知识库管理            │
│ base/*.md      │   导入文档 → 自动向量化 → 配置元数据       │
│                │                                          │
│ ai/workflows/  │ → 苍穹 Agent 平台 → 任务流编排            │
│ *.yaml         │   对照 yaml 在 Web UI 配置各节点           │
│                │                                          │
│ data/          │ → 苍穹基础资料管理                         │
│ dictionaries/  │   导入字典/种子数据                        │
│ mock/*.json    │   配置演示用模拟账号                        │
│                │                                          │
└────────────────┴──────────────────────────────────────────┘
```

### 2.3 嵌入式控件 Java 插件骨架

```java
// 苍穹到位后实现这个类
// 依赖: 苍穹 SDK（kd.bos.gptas.api.embedctrl.EmbeddedControlService）

public class SandplayEmbeddedPlugin extends AbstractFormPlugin {

    @Override
    public void customEvent(CustomEventArgs args) {
        String methodName = args.getMethodName();
        Map<String, Object> params = args.getParams();

        switch (methodName) {
            case "openAgent":
                // 读取当前页面沙盘元素
                List<SandplayElement> elements = readElementsFromPage();
                // 构造 Agent 上下文
                String context = buildContext(elements);
                // 打开嵌入式控件
                EmbeddedControlService.show(formView, agentParam, showStyle);
                break;

            case "chat":
                // 用户发送消息 → 调Agent
                EmbeddedControlService.chat(
                    chatSessionId, skillId, userInput,
                    Map.of("sandplayContext", context)  // 传递页面数据
                );
                break;

            case "stopStream":
                EmbeddedControlService.stop(chatSessionId, taskId, flowId);
                break;
        }
    }

    private String buildContext(List<SandplayElement> elements) {
        // 把沙盘元素列表序列化为 Agent 可理解的文本
        return "当前沙盘包含" + elements.size() + "个元素：" +
            elements.stream()
                .map(e -> e.getCategory() + "(" + e.getElementId() + ")")
                .collect(Collectors.joining(", "));
    }
}
```

### 2.4 迁移步骤时序

```
阶段1: 苍穹环境到手第1天
  ├── 创建最小领域模型（对着 CSV 映射表建）
  ├── 部署一个 Java 插件（上传 jar → 返回固定 JSON → 确认日志可见）
  ├── 创建一个 Agent（粘贴沙盘 Prompt → RAG检索验证）
  ├── 拖一个 ai-embedding-ctrl → 确认弹窗出现
  └── 更新 docs/环境基线.md

阶段2: 第3-5天
  ├── 迁移 SandplayGeometryService → 苍穹 Java 插件
  ├── 迁移 KWC Canvas → 苍穹 KWC 组件
  ├── 实现 KingdeeAdapter → 替换 LocalMockAdapter
  └── 沙盘端到端链路打通

阶段3: 第5-7天
  ├── 迁移笔迹检测 KWC 组件（A负责）
  ├── 注册笔迹分析 Agent
  ├── 两个页面的嵌入式控件联调
  └── 知识库上下文联动验证

阶段4: 第7-8天
  ├── 安装包导出 → 全新环境安装验证
  ├── 所有 Agent 工具幂等/超时/降级测试
  └── 比赛演示录制
```

### 2.5 一个具体的例子：沙盘 Canvas 怎么迁移

```
本地文件: local/frontend-prototype/sandplay-canvas.html (293行)

迁移操作:
1. 苍穹 → KWC组件管理 → 新建组件 "SandplayCanvas"
2. 把 HTML 结构粘贴进模板
3. 适配点:
   ┌─────────────────────────────────────┐
   │ 本地写法           → 苍穹 KWC 写法   │
   ├─────────────────────────────────────┤
   │ canvas.addEventListener → KWC事件系统│
   │ document.getElementById  → KWC组件ref│
   │ fetch('/api/...')       → KWC服务调用 │
   │ CSS 内联               → KWC样式系统  │
   │ console.log             → KWC日志API  │
   └─────────────────────────────────────┘
4. 保存 → 发布 → 在页面设计器里拖入该组件
5. 拖入 ai-embedding-ctrl → 绑定沙盘智能体
6. 写 Java 插件（上方的骨架代码）→ 上传 jar
7. 端到端测试: 拖元素 → 点AI助手 → 对话 → 结果回填
```

---

## 三、当前进度

### 3.1 总体进度

```
████████████████████░░░░░░░░  ≈ 60%

已完成: ~42 / 70 任务
待完成: ~28 任务
阻塞: 6 项需苍穹 KWC SDK, 6 项需 Spring Boot 环境
```

### 3.2 已交付资产清单

**接口契约** — 100%

| 文件 | 说明 |
|------|------|
| `contracts/openapi/sandplay-analysis.yaml` | 沙盘分析 API，OpenAPI 3.0 |
| `contracts/openapi/htp-analysis.yaml` | 房树人分析 API，含降级响应 |
| `contracts/schemas/sandplay-element.schema.json` | 沙盘元素 JSON Schema |
| `contracts/schemas/htp-questionnaire.schema.json` | 房树人问卷 JSON Schema |
| `contracts/schemas/agent-output.schema.json` | Agent 输出统一 Schema |
| `contracts/errors/multimodal-error-codes.yaml` | 17 个统一错误码 |
| `contracts/mappings/sandplay-field-mapping.csv` | 沙盘四列映射表 |
| `contracts/mappings/htp-field-mapping.csv` | 房树人四列映射表 |

**Java 领域服务** — 100%

| 文件 | 说明 |
|------|------|
| `pom.xml` | Maven 项目（Java 17 + JUnit 5 + Jackson） |
| `platform/PlatformAdapter.java` | 平台适配器接口（5 方法族） |
| `platform/LocalMockAdapter.java` | 本地 Mock 实现（幂等/降级/RAG） |
| `platform/PlatformAdapterFactory.java` | 适配器工厂 |
| `platform/AgentException.java` / `MultimodalException.java` / `ToolExecutionException.java` | 异常类 |
| `sandplay/SandplayGeometryService.java` | 几何特征提取（DBSCAN/象限/邻接） |
| `htp/HTPObservationService.java` | 视觉观察服务（含降级） |
| `safety/ContentFilterService.java` | 内容安全过滤（14+术语替换/15+危机词） |
| `controller/SandplayAnalysisController.java` | 沙盘分析控制器 |
| `controller/HTPAnalysisController.java` | 房树人分析控制器 |
| `data/SandplayLayoutGenerator.java` | 沙盘布局生成器 |
| `model/*.java` | 9 个 DTO 模型类 |

| 测试 | 用例数 |
|------|--------|
| `PlatformAdapterTest.java` | 16 |
| `SandplayGeometryServiceTest.java` | 15+ |
| `HTPObservationServiceTest.java` | 5 |

**AI 资产** — 90%

| 文件 | 说明 |
|------|------|
| `ai/prompts/sandplay-analysis-agent-v1.md` | 沙盘 Agent Prompt（五段式 + Few-shot × 2） |
| `ai/prompts/htp-analysis-agent-v1.md` | 房树人 Agent Prompt（观察与推测分离 + 降级示例） |
| `ai/tools/save_sandbox_record.schema.json` | 保存沙盘记录工具 |
| `ai/tools/save_htp_record.schema.json` | 保存房树人记录工具 |
| `ai/tools/get_rag_context.schema.json` | RAG 检索工具 |
| `ai/workflows/sandplay-analysis-workflow.yaml` | 沙盘任务流（7 步） |
| `ai/workflows/htp-analysis-workflow.yaml` | 房树人任务流（含降级分支） |
| `ai/knowledge-base/sandplay-methodology/` | 沙盘方法论 RAG 文档（1 篇，待扩至 5+） |
| `ai/knowledge-base/htp-methodology/` | 房树人方法论 RAG 文档（1 篇，待扩至 5+） |
| `ai/eval/sandplay-eval-set.json` | 沙盘评测集（10 条） |
| `ai/safety/safety-test-cases.json` | 安全测试集（15 条） |

**数据与前端** — 80%

| 文件 | 说明 |
|------|------|
| `data/dictionaries/sandplay-elements.json` | 35 个沙盘元素字典 |
| `data/mock/sandplay-samples.json` | 12 个沙盘布局样本 |
| `local/frontend-prototype/sandplay-canvas.html` | 沙盘 Canvas 原型（293行，完整交互） |
| `local/frontend-prototype/assets/sandplay/*.svg` | 36 个元素图标 |

**文档** — 60%

| 文件 | 说明 |
|------|------|
| `openspec/changes/role-b-multimodal-agent/proposal.md` | 变更提案 |
| `openspec/changes/role-b-multimodal-agent/design.md` | 技术设计（7 决策 / 风险 / 开放问题） |
| `openspec/changes/role-b-multimodal-agent/specs/*/spec.md` | 5 个能力规格（30+ 需求 / 60+ 场景） |
| `openspec/changes/role-b-multimodal-agent/tasks.md` | 70 个可跟踪任务 |
| `docs/角色B-进度总结.md` | 详细进度报告 |
| `kingdee/evidence/sandplay-htp-migration-checklist.md` | 苍穹迁移检查清单 |

### 3.3 MVP 达成缺口

```
✅ 沙盘 Canvas 原型 — 完成
✅ 沙盘特征提取 — 完成
✅ 沙盘 Agent Prompt — 完成
✅ 沙盘 RAG 知识库 — 完成（1篇）
✅ 嵌入式控件 Java 插件骨架 — 完成（框架代码）

🔴 笔迹采集 Canvas 原型 — 未开始（角色A任务，B需配合Agent）
🔴 笔迹分析 Agent Prompt — 未开始
🔴 笔迹 RAG 知识库 — 未开始
🔴 两个界面智能体上下文联动 — 未开始
🔴 KingdeeAdapter 实现 — 阻塞于苍穹环境
🔴 KWC 组件迁移 — 阻塞于苍穹 KWC SDK
```

### 3.4 沙盘 Canvas 原型可验收功能

直接浏览器打开 `local/frontend-prototype/sandplay-canvas.html`：

| 功能 | 操作 |
|------|------|
| 拖拽添加元素 | 从左侧元素库拖到画布 |
| 移动元素 | 点击选中（蓝色高亮），拖拽移动 |
| 分类筛选 | 顶部标签过滤（人物/动物/建筑/植物/自然/交通/符号） |
| 撤销/重做 | 工具栏按钮（50步历史） |
| 清空画布 | 带确认弹窗 |
| 网格辅助线 | 切换 50px 网格 + 中心十字线 |
| 文字描述 | 底部输入区，实时字符计数（0/500） |
| 保存分析 | 序列化为 JSON → 模拟 API 调用（带 loading 动画） |
| 控制台查看 | F12 → 查看提交的数据结构 |

---

## 四、文件索引

```
mindLine/
├── docs/
│   ├── 三人分工.md                              ← 角色分工权威文档
│   ├── 项目总方案.md                             ← 产品/架构/里程碑
│   ├── 心迹AI整体技术路线.md                      ← 技术细节（Agent/RAG/多模态）
│   ├── 角色B-进度总结.md                         ← 详细进度（本文档的详细版）
│   └── MVP方案-迁移方法-当前进度.md               ← 【本文档】
│
├── contracts/                                   ← API契约层
│   ├── openapi/sandplay-analysis.yaml
│   ├── openapi/htp-analysis.yaml
│   ├── schemas/*.json
│   ├── errors/multimodal-error-codes.yaml
│   └── mappings/*.csv
│
├── local/java-domain/                           ← Java领域服务
│   ├── pom.xml
│   └── src/main/java/com/mindline/
│       ├── platform/    PlatformAdapter / LocalMockAdapter / Factory
│       ├── model/       9 个 DTO
│       ├── sandplay/    SandplayGeometryService
│       ├── htp/         HTPObservationService
│       ├── safety/      ContentFilterService
│       ├── controller/  SandplayAnalysisController / HTPAnalysisController
│       └── data/        SandplayLayoutGenerator
│
├── local/frontend-prototype/                    ← KWC 原型
│   └── sandplay-canvas.html                    ← 可直接浏览器打开
│
├── ai/                                          ← AI 资产（直接导入苍穹）
│   ├── prompts/         Agent System Prompt
│   ├── tools/           工具 JSON Schema
│   ├── workflows/       任务流 YAML
│   ├── knowledge-base/  RAG 语料
│   ├── eval/            离线评测集
│   └── safety/          安全测试用例
│
├── data/                                        ← 模拟数据
│   ├── dictionaries/    元素库字典
│   └── mock/            沙盘样本
│
└── kingdee/evidence/                            ← 苍穹迁移
    └── sandplay-htp-migration-checklist.md
```
能做什么 vs 不能做什么

┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  ✅ 本地能做的:                                               │
│  · 写 EmbeddedAgentPlugin 的完整 Java 代码框架                │
│  · 写 switch(event): openAgent / chat / stop / sendMessage  │
│  · 写 buildPageContext() 读取沙盘/笔迹数据                    │
│  · 写 LocalMockEmbeddedService 模拟对话                      │
│  · 写 KWC 页面的 AI 按钮和 fireCustomEvent 调用               │
│                                                             │
│  🔴 本地不能做的:                                             │
│  · 编译需要 kd.bos.gptas.api.embedctrl.EmbeddedControlService│
│    这个类在 cosmic 的 bos jar 里，本地没有                     │
│  · 实际运行嵌入式控件弹窗（需要苍穹运行时环境）                  │
│                                                             │
│  迁移时做的事:                                                │
│  · 把写好的 .java 文件放进 cosmic/cloud-app/plugin/other/     │
│  · Gradle 编译 → bos jar 提供 SDK → 编译通过                  │
│  · DebugApplication.main() 启动 → 控件可用                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
具体来说
你在本地写的代码搬到 cosmic 后，只需要改 import 这一个地方：


// 本地写的（Mock）:
// EmbeddedAgentService 是我们自己定义的接口
EmbeddedAgentService.show(...)

// 迁移到 cosmic 后（真实）:
import kd.bos.gptas.api.embedctrl.EmbeddedControlService;  // ← bos jar 提供
EmbeddedControlService.show(formView, agentParam, showStyle);
方法名和参数基本一致（因为之前你就是照着官方文档的 SDK API 设计的），迁移就是替换 import + 删除 Mock 类。

结论
可以放心在本地写，迁移成本很低——换一个 import，删掉 Mock 实现，在 cosmic 里 gradle build 就通了