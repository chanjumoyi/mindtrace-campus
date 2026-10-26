# 心迹AI（MindLine）

心迹AI是面向大学生的心理健康智能交互平台。项目依据《心迹AI——大学生心理健康智能交互平台立项报告》重整，采用 Vue 3、FastAPI 与 MySQL，围绕日常对话、电子手账、情绪记录、笔迹行为、房树人、心理沙盘、冥想练习和心理科普展开。

当前版本是用于技术验证的研究原型，不代表立项报告中的全部功能已经完成。实现状态和验收口径以 [需求清单](docs/01-product/requirements.md) 为准。

> 安全边界：平台只提供心理健康教育、日常支持和非诊断性辅助观察，不替代心理咨询师、医疗机构或紧急服务。笔迹、绘画和沙盘结果不能单独用于人格判断或医学诊断。

## 当前范围

- 核心产品：AI陪伴、情绪打卡、电子手账、冥想与科普。
- 探索模块：笔迹行为特征、房树人辅助观察、AI辅助沙盘。
- 数据原则：最小化采集、显式授权、敏感数据隔离、可删除、可审计。
- 评估计划：在伦理审查、正式量表使用条件确认和知情同意后，按照[笔迹数据集与数位板采集规范](docs/03-data/handwriting-collection-and-dataset-spec.md)开展测量；量表分数不等于诊断。

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

必须使用 Python 3.12 创建虚拟环境：固定的 `pydantic==2.11.x` 在 3.13/3.14 上没有预编译包，安装会在 `pydantic-core` 处失败。研究数据适配器将在统一轨迹 Schema 2.0 冻结后单独声明依赖，不复用后端运行时环境。

## 目录

```text
mindtrace-campus/
├─ frontend/                 # Vue 3 Web 应用与沙盘/笔迹交互资源
├─ backend/                  # FastAPI、MySQL 数据模型、AI 与笔迹服务
├─ research/                 # 离线研究资产、数据适配器和实验（不被线上服务导入）
├─ docs/                     # 产品、架构、数据、API、开发和协作文档
├─ tests/                    # 后端、算法和前端纯逻辑测试
├─ upload-server.ps1         # Windows 书写采集上传接收器
├─ update-upload-server.ps1  # 上传接收器的备份、更新与健康检查
├─ watch-mindtrace.ps1        # Windows 网页、上传服务与采集文件监控
├─ docker-compose.yml        # MySQL + FastAPI + Vue/Nginx
└─ .env.example              # 不含密钥的配置模板
```

所有队友在编码前必须阅读[项目架构与开发基线](docs/02-architecture/README.md)。产品范围见[需求清单](docs/01-product/requirements.md)，真人笔迹研究见[笔迹数据集与数位板采集规范](docs/03-data/handwriting-collection-and-dataset-spec.md)。

书写采集上传服务的代码位于仓库根目录：[上传接收器](upload-server.ps1)、[更新脚本](update-upload-server.ps1)、[监控窗口](watch-mindtrace.ps1)。监控默认每 5 秒刷新服务健康、上传鉴权模式和文件统计，支持 `-Once` 单次检查；首次替换旧监控脚本后需要重新打开窗口。Windows 服务器部署和监控启动步骤见[采集器部署说明](deploy/handwriting-collector/README.md)。

移动采集器完成页仅显示采集和上传状态，评分保存在 JSON 中。1.8.0 导出增加输入有效性、设备档案和分开的停顿指标，定义及旧数据缺失值处理见[采集导出格式说明](docs/06-development/collector-export-1.8.md)。

## 研究数据

真实对话、笔迹、量表、身份信息和参与者数据不得提交到 Git。所有本地敏感数据和下载的数据集必须放在仓库之外的受控目录，或放入明确被 Git 忽略的 `research/private/`。仓库内示例必须是合成数据。
