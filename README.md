# 心迹AI（MindLine）

面向高校学生的心理健康智能关爱平台，中国软件杯 A6“新质校园智能体应用”参赛项目。

项目以金蝶 AI 苍穹为核心底座，围绕笔迹分析、房树人（HTP）、心理沙盘和 AI 陪伴构建多模态智能体应用，形成“感知—观察—评估—干预—转介—随访—复盘”的业务闭环。

> 产品定位：提供心理健康教育、日常支持、风险筛查和专业转介辅助；不进行医学诊断，不替代心理咨询师或医疗机构。

## 核心模块

| 模块 | 当前能力 | 主要技术 |
|---|---|---|
| 动态笔迹分析 | Pencil 轨迹采集、压力/速度/停顿特征、个人基线、原型评分 | Pointer Events、Python、岭回归 |
| 笔迹知识库 | 《笔迹心理学》OCR、带页码分块、假设审核、本地检索 | Windows OCR、RAG、规则审计 |
| 房树人分析 | 图像客观观察、问卷补充、Agent 解释 | 多模态模型、Prompt、RAG |
| 心理沙盘 | 元素拖拽、布局计算、结构化观察 | Canvas、Java、Agent 工具调用 |
| 公共平台 | 登录、权限、文件、审计、AI 网关、任务状态 | Spring Boot、PostgreSQL、Docker |
| 苍穹迁移 | KWC 组件、Java 插件、Agent 工具和领域模型资产 | 金蝶 AI 苍穹、KWC、Java |

## 快速开始

### 1. 启动笔迹采集器

在 Windows PowerShell 中运行：

```powershell
Set-Location D:\project\mindLine
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\start_handwriting_collector.ps1
```

脚本会输出电脑本机地址和供同一 Wi-Fi 下平板访问的地址。采集页面默认只接受触控笔输入；PC 调试模式需手动开启。

### 2. 启动前端原型

```powershell
Set-Location local\frontend-prototype
python -m http.server 8082 --bind 127.0.0.1
```

浏览器访问：

- `http://127.0.0.1:8082/sandplay-canvas.html`
- `http://127.0.0.1:8082/handwriting-canvas.html`
- `http://127.0.0.1:8082/ai-chat-widget.html`

### 3. 运行 Java 领域测试

需要 JDK 17 和 Maven：

```powershell
Set-Location local\java-domain
mvn test
```

### 4. 启动 Docker 全栈

```powershell
docker compose up -d
```

- 公共前端：`http://localhost:8088`
- 后端健康检查：`http://localhost:8080/actuator/health`
- Mock Agent：`http://localhost:8090/health`

模拟账号：

- `student_demo / demo123`
- `counselor_demo / demo123`
- `admin_demo / admin123`

关闭服务：

```powershell
docker compose down
```

## 笔迹数据与模型流程

原始笔迹和心理自评属于敏感研究数据，只保存在 `data/handwriting-private/`，不得提交到 Git 仓库。

```powershell
# 检查单条轨迹
python scripts\inspect_handwriting_trace.py path\to\trace.json

# 生成全部结构化特征
python scripts\build_handwriting_dataset.py

# 训练并执行留一参与者评估
python scripts\train_handwriting_baseline.py

# 检索本地书籍知识库
python scripts\search_handwriting_book.py "书写速度 下笔重 综合分析" --top-k 3
```

当前模型用于比赛原型和工程链路验证。正式评估必须按参与者划分训练集与测试集，禁止随机拆分同一人的重复样本后宣称泛化准确率。

## 项目结构

```text
mindLine/
├─ ai/                    # Agent Prompt、工作流、工具定义、公开RAG语料
├─ contracts/             # OpenAPI、JSON Schema、错误码和字段映射
├─ data/                  # 模拟数据；私人笔迹目录由Git忽略
├─ database/              # PostgreSQL DDL、迁移和种子数据
├─ deliverables/          # PPT、演示视频、设计说明书和测试报告
├─ docs/                  # 项目、比赛和技术文档
├─ kingdee/               # 苍穹低代码、KWC、Agent和部署资产
├─ knowledge/             # 笔迹书籍假设、RAG清单和安全策略
├─ local/                 # Java服务、前端原型、采集器和Mock Agent
├─ references/private/    # 私有OCR文本和知识分块，不进入Git
├─ scripts/               # 数据、模型、OCR、校验和启动脚本
└─ tests/                 # 契约、集成、端到端和安全测试
```

## 重要文档

- [项目总方案](docs/项目总方案.md)
- [整体技术路线](docs/心迹AI整体技术路线.md)
- [MVP与迁移进度](docs/MVP方案-迁移方法-当前进度.md)
- [笔迹采集与数据集方案](docs/handwriting/01-采集与数据集起步方案.md)
- [笔迹证据矩阵](docs/handwriting/03-笔迹心理学证据矩阵.md)
- [苍穹迁移方案](docs/苍穹迁移方案.md)
- [测试报告模板](docs/测试报告-模板.md)

## 数据、安全与伦理

- 比赛和演示只使用模拟数据或取得明确同意的匿名样本。
- 笔迹书籍内容只作为待验证假设和解释材料，不作为真实心理标签。
- 单一笔迹特征不得直接生成性格定论、疾病诊断或危机等级。
- Agent 输出应区分“客观观察—待验证主题—探索问题”，并保留依据、页码和审计记录。

## 当前阶段

本地已完成沙盘、HTP、动态笔迹采集、特征工程、基线模型、书籍 OCR/RAG 和 AI 对话原型。苍穹环境到位后，重点完成真实 Agent 注册、知识库向量索引、工具接入、KWC 组件迁移和端到端演示闭环。
