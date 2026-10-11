# 新成员环境安装与项目测试指南

状态：当前版本适用

最后更新：2026-10-11

适用系统：Windows 10/11（PowerShell）

本文是新成员首次拉取、启动和测试项目的唯一安装入口。项目当前可运行拓扑只有 `frontend + backend + mysql`；Redis、Celery、MinIO 等属于后续集成阶段能力，不是当前测试环境的前置条件。

## 1. 先选择运行方式

| 方式 | 适合谁 | 必须安装 | 特点 |
| --- | --- | --- | --- |
| Docker 一键运行（推荐） | 只测试功能、验收页面、联调 | Git、Docker Desktop | 环境最一致，不必单独安装 Python、Node.js 或 MySQL |
| 本地开发运行 | 需要改代码、断点调试、运行全部质量检查 | Git、Python 3.12、Node.js 22 LTS；MySQL 可继续使用 Docker | 启动和调试更快，但首次配置更多 |

组员如果只是验证功能，选择 Docker 方式即可。不要为了测试项目额外安装原生 MySQL、Vue CLI、Java、Maven、Kubernetes 或任何金蝶平台组件。

## 2. 当前需要和不需要安装的内容

### 2.1 所有人必须安装

1. **Git for Windows**：用于拉取和更新仓库。
2. **Docker Desktop**：推荐的统一测试环境，已经包含 Docker Compose。
3. **现代浏览器**：推荐最新版 Microsoft Edge 或 Chrome，用于页面测试和开发者工具。

### 2.2 只有本地开发时安装

1. **Python 3.12.x**：后端和算法环境。请不要自行换成 3.13 或其他大版本。
2. **Node.js 22 LTS**：前端环境。项目镜像使用 Node 22；Vite 8 要求 Node 20.19+ 或 22.12+，团队统一使用 Node 22 LTS。
3. **Visual Studio Code**：团队推荐编辑器，但不是运行项目的硬性依赖。

### 2.3 当前不要额外安装

- **MySQL 桌面版 / MySQL Workbench**：Docker 已提供 MySQL 8.4；除非负责数据库专项工作，否则不需要。
- **Redis、Celery、MinIO**：架构为后续集成阶段预留，当前 `docker-compose.yml` 没有启用。
- **Vue CLI、全局 Vite、全局 Uvicorn**：项目依赖由 `npm` 和 Python 虚拟环境管理，不要全局安装。
- **Java、Spring Boot、Maven、Gradle**：本项目后端是 FastAPI，不使用 Java 技术栈。
- **金蝶 AI 苍穹、KWC 或相关插件**：已经移出项目范围。
- **真实大模型密钥**：默认 `LLM_MODE=mock`，普通功能测试不需要 DeepSeek 密钥。

## 3. Windows 安装教程

### 3.1 安装 Git

推荐在 PowerShell 中执行：

```powershell
winget install --id Git.Git -e --source winget
```

安装后关闭并重新打开 PowerShell，确认：

```powershell
git --version
```

也可以从 [Git for Windows 官方页面](https://git-scm.com/install/windows)下载安装程序，保持默认选项即可。

项目使用 SSH 地址。如果尚未配置 GitHub SSH 密钥，按照 [GitHub 官方 SSH 指南](https://docs.github.com/zh/authentication/connecting-to-github-with-ssh)生成并添加密钥，然后验证：

```powershell
ssh -T git@github.com
```

首次连接出现主机指纹确认时，核对提示后输入 `yes`。如果出现 `Permission denied (publickey)`，说明 GitHub 账号还没有登记当前电脑的公钥。

### 3.2 安装 Docker Desktop（推荐测试方式）

1. 以管理员身份打开 PowerShell，安装或更新 WSL：

   ```powershell
   wsl --install
   wsl --update
   ```

2. 按系统提示重启电脑。
3. 从 [Docker Desktop for Windows 官方安装页](https://docs.docker.com/desktop/setup/install/windows-install/)下载安装。
4. 启动 Docker Desktop，使用默认的 WSL 2 后端，等待状态显示 Docker Engine 已运行。
5. 在新的 PowerShell 中确认：

   ```powershell
   docker --version
   docker compose version
   ```

Docker Desktop 已经包含 Compose，不要再单独安装旧版 `docker-compose`。

### 3.3 安装 Python 3.12（仅本地开发）

推荐在 PowerShell 中安装项目指定的大版本：

```powershell
winget install --id Python.Python.3.12 -e --source winget
```

也可以从 [Python 3.12.10 官方发布页](https://www.python.org/downloads/release/python-31210/)下载 Windows 64 位安装程序。安装第一页勾选 **Add python.exe to PATH**，并保留 `pip` 和 `venv` 组件。不要直接安装 Python 官网首页推荐的其他大版本来替代 3.12；部分固定依赖在新大版本上可能没有兼容的预编译包。

安装后确认：

```powershell
py -3.12 --version
```

输出应以 `Python 3.12` 开头。

### 3.4 安装 Node.js 22 LTS（仅本地开发）

从 [Node.js 官方下载页](https://nodejs.org/en/download)安装 Node.js 22 LTS。项目不要求全局安装 Vue 或 Vite。

安装后确认：

```powershell
node --version
npm --version
```

Node 版本至少应为 `v22.12.0`。团队统一 Node 22 LTS，不追随 Current 奇数版本或自行切换大版本。

### 3.5 安装 VS Code 与推荐插件（建议）

从 [VS Code 官方 Windows 安装页](https://code.visualstudio.com/docs/setup/windows)安装 User Setup 版本。安装完成后可在扩展面板按 ID 搜索，或一次执行：

```powershell
code --install-extension Vue.volar
code --install-extension ms-python.python
code --install-extension ms-python.vscode-pylance
code --install-extension charliermarsh.ruff
code --install-extension esbenp.prettier-vscode
code --install-extension ms-azuretools.vscode-docker
code --install-extension EditorConfig.EditorConfig
```

| 插件 | 用途 | 是否建议 |
| --- | --- | --- |
| [Vue - Official](https://marketplace.visualstudio.com/items?itemName=Vue.volar) | Vue 3 语法、类型和模板支持 | 前端必装 |
| [Python](https://marketplace.visualstudio.com/items?itemName=ms-python.python) | Python 调试、测试和环境选择 | 后端必装 |
| [Pylance](https://marketplace.visualstudio.com/items?itemName=ms-python.vscode-pylance) | Python 类型与代码补全 | 后端必装 |
| [Ruff](https://marketplace.visualstudio.com/items?itemName=charliermarsh.ruff) | Python 检查和格式化 | 后端必装 |
| [Prettier](https://marketplace.visualstudio.com/items?itemName=esbenp.prettier-vscode) | 前端代码格式化 | 前端必装 |
| [Docker](https://marketplace.visualstudio.com/items?itemName=ms-azuretools.vscode-docker) | 查看容器、镜像和日志 | 建议安装 |
| [EditorConfig](https://marketplace.visualstudio.com/items?itemName=EditorConfig.EditorConfig) | 统一缩进、换行和编码 | 建议安装 |

如果使用 JetBrains 等其他编辑器，不必安装这些 VS Code 插件，但必须遵守仓库格式和测试命令。

## 4. 首次拉取项目

建议把仓库放在短且不含中文或空格的路径，例如 `D:\project`：

```powershell
Set-Location D:\project
git clone git@github.com:chanjumoyi/mindtrace-campus.git
Set-Location mindtrace-campus
git switch main
git pull --ff-only origin main
```

确认当前分支和工作区：

```powershell
git branch --show-current
git status
```

当前分支应为 `main`。组员不要直接在 `main` 上开发；本次只进行测试时不要修改或提交文件。

## 5. Docker 一键启动与验收（推荐）

### 5.1 创建本地配置

在仓库根目录执行：

```powershell
Copy-Item .env.example .env
```

`.env` 只保存在自己电脑上，严禁提交。普通测试保持 `LLM_MODE=mock` 和空的 `DEEPSEEK_API_KEY`，不需要任何付费 API。

### 5.2 启动项目

确保 Docker Desktop 正在运行，然后执行：

```powershell
docker compose up --build
```

第一次启动会下载基础镜像并构建前后端，耗时取决于网络。看到前端、后端和 MySQL 均正常运行后访问：

- Web 页面：<http://localhost:8080>
- API 文档：<http://localhost:8000/docs>
- 健康检查：<http://localhost:8000/health>

建议按以下顺序完成冒烟测试：

1. 健康检查页面可访问，返回成功状态。
2. Web 首页可正常加载，浏览器控制台没有持续报错。
3. 完成一次情绪打卡并刷新页面，数据仍可读取。
4. 打开 AI 对话，确认 Mock 模式能返回响应。
5. 进入笔迹或研究入口时，只使用合成内容，不输入真实个人隐私。

### 5.3 日常停止和再次启动

按 `Ctrl+C` 停止前台日志，再执行：

```powershell
docker compose down
```

这会停止容器，但保留 MySQL 测试数据。下次执行 `docker compose up` 即可恢复。

> `docker compose down -v` 会删除数据库卷及其中全部本地测试数据。只有明确需要重置数据库时才能使用。

查看后端日志：

```powershell
docker compose logs -f backend
```

## 6. 本地开发环境（需要改代码时）

### 6.1 后端

在仓库根目录执行：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r backend\requirements-dev.txt
$env:DATABASE_URL='sqlite:///./mindline-dev.db'
python -m uvicorn app.main:app --app-dir backend --reload
```

后端开发地址为 <http://localhost:8000>。这里使用本地 SQLite 作为轻量开发数据库；正式的 Docker 联调仍使用 MySQL 8.4。

如果 PowerShell 阻止虚拟环境激活，只对当前窗口临时放行：

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\.venv\Scripts\Activate.ps1
```

### 6.2 前端

另开一个 PowerShell 窗口：

```powershell
Set-Location D:\project\mindtrace-campus\frontend
npm ci
npm run dev
```

访问 <http://localhost:5173>。Vite 会把 `/api` 和 `/health` 请求代理到本机 `8000` 端口，因此后端需要同时运行。

使用 `npm ci` 可以严格按锁文件安装依赖。只有明确升级依赖时才使用 `npm install` 并提交锁文件变化。

## 7. 拉取后必须执行的检查

只做 Docker 功能测试时，至少完成第 5 节的冒烟测试。参与开发的组员在提交前还需执行：

```powershell
.\.venv\Scripts\python -m pytest tests
node tests/test_pointer_normalization.cjs
npm run format:check --prefix frontend
npm run build --prefix frontend
```

检查全部成功后再提交代码。测试只能使用合成或匿名数据，不得把真实对话、量表、笔迹或身份信息放进仓库。

## 8. 日常同步 main 的操作

每次开始测试前：

```powershell
git switch main
git pull --ff-only origin main
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
docker compose up --build
```

如果组员需要开发，应从最新 `main` 新建自己的功能分支，不要直接向 `main` 提交：

```powershell
git switch main
git pull --ff-only origin main
git switch -c feature/简短功能名
```

分支名称使用英文小写和连字符，例如 `feature/mood-calendar`。

## 9. 常见问题

### Docker 命令存在但无法连接

先启动 Docker Desktop，等待引擎完全就绪，再执行 `docker compose up`。如果 WSL 异常，管理员 PowerShell 执行 `wsl --update` 后重启电脑。

### 3306、8000 或 8080 端口被占用

执行以下命令查找占用进程：

```powershell
Get-NetTCPConnection -LocalPort 3306,8000,8080 -ErrorAction SilentlyContinue
```

关闭冲突的本地 MySQL、Web 服务或旧容器后重试。不要随意修改团队约定端口并提交到仓库。

### Node 版本导致 Vite 启动失败

执行 `node --version`。低于 22.12 时升级到 Node 22 LTS，然后删除本机 `frontend\node_modules` 并重新运行 `npm ci`；不要删除或改写仓库里的 `package-lock.json`。

### Python 找不到或版本不对

执行 `py -0p` 查看电脑中的 Python 版本，再用 `py -3.12` 创建虚拟环境。不要把全局 Python 包当作项目依赖。

### 数据库状态异常

先查看 `docker compose logs mysql backend`。只有确定本地测试数据可以全部丢弃时，才执行：

```powershell
docker compose down -v
docker compose up --build
```

### Git 拉取提示本地修改冲突

不要强制覆盖，也不要执行 `git reset --hard`。先运行 `git status`，保存自己的工作，再向负责仓库合并的同学确认处理方式。

## 10. 安全与数据红线

- 不提交 `.env`、API 密钥、数据库、日志、模型私有产物或个人联系方式。
- 不用真实同学的心理记录、私人对话、量表、笔迹、图像或身份信息做开发测试。
- 不在截图、群聊或问题单中暴露密钥和敏感内容。
- 当前产品只用于研究原型和非诊断性辅助，不依据结果给出医学诊断或人格定论。
- 如需启用真实 LLM，每位开发者使用自己的本地密钥；密钥只写入 `.env`。

## 11. 新成员阅读顺序

所有组员先按以下顺序阅读，不要只看启动命令：

1. [项目 README](../../README.md)：项目定位、当前范围、技术栈和安全边界。
2. [文档总览](../README.md)：规范优先级、文档导航和已经移出范围的内容。
3. **本文**：安装环境、启动项目、执行测试和排查问题。
4. [产品范围与功能清单](../01-product/README.md)：哪些功能已规划、如何界定研究原型。
5. [系统架构说明](../02-architecture/README.md)：后续开发必须遵守的模块边界、依赖方向、数据和部署规范。
6. [数据与隐私规范](../03-data/README.md)：敏感数据、授权、删除、研究数据和禁止提交内容。
7. [协作规范](../07-collaboration/README.md)：分工、分支、提交、评审和架构决策流程。

再按职责补充阅读：

| 职责 | 需要补充阅读 |
| --- | --- |
| 只参与功能测试 | [需求清单](../需求清单.md)、本文第 5 节与第 10 节 |
| 前端开发 | [API 规范](../04-api/README.md)、系统架构说明中的前端边界和状态处理 |
| 后端开发 | [API 规范](../04-api/README.md)、[数据规范](../03-data/README.md)、系统架构说明中的模块模板 |
| AI / 算法 / 研究 | [AI 与多模态规范](../05-ai/README.md)、数据与隐私规范、系统架构说明中的异步任务与模型版本部分 |
| 负责合并或发布 | [开发、测试与发布规范](./README.md)、[ADR-0001](../07-collaboration/decisions/0001-modular-monolith.md) |

## 12. 新成员完成标准

新成员完成以下项目，才算环境准备完毕：

- [ ] `git --version`、`docker --version` 和 `docker compose version` 正常输出。
- [ ] 已通过 SSH 拉取仓库，并处于最新 `main`。
- [ ] 已从 `.env.example` 创建本地 `.env`，且保持 Mock 模式。
- [ ] `docker compose up --build` 启动成功。
- [ ] Web、API 文档和健康检查三个地址均能访问。
- [ ] 已完成情绪打卡、Mock 对话等冒烟测试。
- [ ] 已阅读项目范围、系统架构、安全边界和协作规范。
- [ ] 参与开发者已额外安装 Python 3.12、Node 22 LTS，并能通过第 7 节检查。

完成后，向组内反馈操作系统版本、运行方式、测试结果和完整错误信息；不要只发送“运行不了”的截图。
