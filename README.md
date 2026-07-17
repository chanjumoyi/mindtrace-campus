# 心迹AI（MindLine）

面向高校学生的心理健康智能关爱平台，中国软件杯 A6"新质校园智能体应用"参赛项目。

项目以金蝶 AI 苍穹为核心底座，通过多模态情绪记录、AI 陪伴、风险分级、自助干预、预约转介和管理驾驶舱，形成"感知—评估—干预—转介—随访—复盘"的业务闭环。

> 产品定位：提供心理健康教育、日常支持、风险筛查和专业转介辅助；不进行医学诊断，不替代心理咨询师或医疗机构。

## 快速启动（本地预览）

无需安装任何依赖，直接在浏览器中打开以下文件即可预览 MVP 前端原型：

```bash
# 方式1: 双击打开（最简单）

local/frontend-prototype/sandplay-canvas.html      # 沙盘画布
local/frontend-prototype/handwriting-canvas.html    # 笔迹检测
local/frontend-prototype/ai-chat-widget.html        # AI 对话浮窗
local/ai-lab/handwriting/collector/index.html       # 笔迹采集器
```

```bash
# 方式2: 本地 HTTP 服务器（推荐，支持跨页面弹窗）

# Python 3
cd local/frontend-prototype
python -m http.server 8082 --bind 127.0.0.1

# 然后浏览器打开:
# http://127.0.0.1:8082/sandplay-canvas.html
# http://127.0.0.1:8082/handwriting-canvas.html
# 页面内点 "AI助手" 可弹出 ai-chat-widget 对话窗
```

```
# 笔迹采集器（角色A）
cd local/ai-lab/handwriting/collector
python -m http.server 8083 --bind 127.0.0.1
# 打开 http://127.0.0.1:8083
```

```bash
# 方式3: Java 单元测试（需 JDK 17 + Maven）
cd local/java-domain
mvn test
# 预期: Tests run: 47, Failures: 0, Errors: 0, Skipped: 0
```

```bash
# 方式4: Docker Compose 全栈（需 Docker）
docker compose up -d
# 公共前端:  http://localhost:8088
# 后端健康:  http://localhost:8080/actuator/health
# Mock Agent: http://localhost:8090/health

# 模拟账号: student_demo / demo123
#          counselor_demo / demo123
#          admin_demo / admin123

# 关闭: docker compose down
# 关闭并清数据: docker compose down -v
```

<br />

## 目录

```text
mindLine/
├─ ai/                    # Prompt、工作流、工具定义、RAG 语料
├─ contracts/             # OpenAPI、JSON Schema、错误码、字段映射
├─ cosmic/                # 金蝶苍穹在线环境初始工程（只读，不修改）
├─ data/                  # 模拟数据字典、样本、生成器
├─ database/              # PostgreSQL DDL、迁移与种子数据
├─ deliverables/          # PPT、演示视频、设计说明书、测试报告
├─ docs/                  # 项目与比赛文档
├─ kingdee/               # 苍穹低代码、KWC、Agent、部署资产
├─ local/                 # 本地 Java 服务、前端原型、算法实验
│  ├─ frontend-prototype/ # 沙盘/笔迹 Canvas 原型 + AI 对话浮窗
│  ├─ java-domain/        # Java 领域服务（几何/笔迹/安全/适配器）
│  ├─ ai-lab/             # AI 实验（笔迹采集器等）
│  ├─ backend/            # C 的 Spring Boot 公共网关
│  └─ mock-agent/         # C 的基础设施 Mock Agent
├─ scripts/               # 校验、构建、模拟数据脚本
└─ tests/                 # 契约、集成、端到端和安全测试
```

## 当前阶段

本地 MVP 原型已完成沙盘和笔迹双模块的 Canvas 交互 + Agent Prompt + RAG 知识库 + AI 对话浮窗。下一步需苍穹环境到位后实现：真实 Agent 注册、嵌入式控件运行、RAG 向量索引、KWC 组件迁移。
