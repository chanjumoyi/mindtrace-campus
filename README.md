# 心迹AI（MindLine）

心迹AI是面向大学生的心理健康智能交互平台。项目依据《心迹AI——大学生心理健康智能交互平台立项报告》重整，采用 Vue 3、FastAPI 与 MySQL，围绕日常对话、电子手账、情绪记录、笔迹行为、房树人、心理沙盘、冥想练习和心理科普展开。

当前版本是用于技术验证的研究原型，不代表立项报告中的全部功能已经完成。实现状态和验收口径以 [需求清单](docs/需求清单.md) 为准。

> 安全边界：平台只提供心理健康教育、日常支持和非诊断性辅助观察，不替代心理咨询师、医疗机构或紧急服务。笔迹、绘画和沙盘结果不能单独用于人格判断或医学诊断。

## 当前范围

- 核心产品：AI陪伴、情绪打卡、电子手账、冥想与科普。
- 探索模块：笔迹行为特征、房树人辅助观察、AI辅助沙盘。
- 数据原则：最小化采集、显式授权、敏感数据隔离、可删除、可审计。
- 评估计划：在伦理审查和知情同意后，使用 PHQ-9、GAD-7、PSS 等标准工具开展前后测；量表分数不等于诊断。

## 技术栈

| 层 | 技术 | 职责 |
|---|---|---|
| Web | Vue 3 + Vite | 响应式学生端与研究功能入口 |
| API | Python 3.12 + FastAPI | REST API、安全策略与多模态编排 |
| 数据 | MySQL 8.4 | 用户授权、手账、打卡与研究记录 |
| AI | DeepSeek 或兼容 LLM，默认 Mock | 支持性对话、可解释摘要与安全降级 |
| 部署 | Docker Compose | 本地一键启动与环境隔离 |

## 快速开始

首次配置电脑、安装 Docker 或准备本地开发环境时，请先阅读[新成员环境安装与项目测试指南](docs/06-development/setup-guide.md)。只进行功能测试的组员不需要单独安装 Python、Node.js 或 MySQL。

```powershell
Copy-Item .env.example .env
docker compose up --build
```

启动后访问：

- Web：`http://localhost:8080`
- API 文档：`http://localhost:8000/docs`
- 健康检查：`http://localhost:8000/health`

前后端独立开发（需要本地开发时安装 Python 3.12 与 Node 22 LTS）：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install -r backend\requirements-dev.txt
$env:DATABASE_URL='sqlite:///./mindline-dev.db'
.\.venv\Scripts\python -m uvicorn app.main:app --app-dir backend --reload

Set-Location frontend
npm ci
npm run dev
```

必须使用 Python 3.12 创建虚拟环境：固定的 `pydantic==2.11.x` 在 3.13/3.14 上没有预编译包，
安装会在 `pydantic-core` 处失败。只运行 `research/` 下的离线脚本时，再额外安装研究依赖：

```powershell
uv pip install --python .venv\Scripts\python.exe -r research\requirements.txt
```

## 目录

```text
mindtrace-campus/
├─ frontend/                 # Vue 3 Web 应用与沙盘/笔迹交互资源
├─ backend/                  # FastAPI、MySQL 数据模型、AI 与笔迹服务
├─ research/                 # Prompt、工作流、公开知识、算法与实验脚本
├─ docs/                     # 与立项报告一致的架构、范围和安全文档
├─ tests/                    # 后端、算法和前端纯逻辑测试
├─ docker-compose.yml        # MySQL + FastAPI + Vue/Nginx
└─ .env.example              # 不含密钥的配置模板
```

详细取舍见 [需求清单](docs/需求清单.md)、[代码规范](docs/代码规范.md)、[立项报告对齐说明](docs/立项报告对齐说明.md) 和 [系统架构](docs/系统架构.md)。

## 研究数据

真实对话、笔迹、量表、身份信息和参与者数据不得提交到 Git。所有本地敏感数据只允许放入 `research/private/` 或 `research/handwriting/private/`。仓库内示例必须是合成或充分匿名的数据。
