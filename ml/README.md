# MindTrace 离线机器学习

依据[完整训练方案第 4.1 节](../docs/05-ai/MindTrace%20Campus：从零开始的完整模型训练与迁移学习方案.md)建立，与采集程序和线上 API 分离。本次仅完成目录整理，尚未实现数据适配、预处理、模型、训练和评估；不会产生模型或预测结果。

## 目录与职责

| 目录 | 内容 |
| --- | --- |
| `configs/` | 数据位置与三个阶段的配置；当前为占位配置 |
| `data/raw/{casia_ondo,emothaw,mindtrace}/` | 原始数据，本地保存，禁止原地清洗 |
| `data/processed/`、`data/splits/` | 派生数据及参与者划分，不提交 Git |
| `src/datasets/` | 各数据源独立读取与字段映射 |
| `src/preprocessing/` | 质量检查、五通道轨迹、离线统计特征 |
| `src/models/` | BiGRU、重建头和预测头 |
| `src/training/` | 自监督、监督、迁移训练 |
| `src/evaluation/` | 指标与参与者隔离验证 |
| `scripts/01_*` 至 `07_*` | 按数据准备、特征、基线、预训练、监督、迁移、评估顺序实现 |
| `checkpoints/`、`experiments/`、`reports/` | 权重、实验输出及可能含敏感信息的报告；默认全部忽略 |

`src/` 文件目前只有职责说明。各脚本支持 `--help`，直接运行会以退出码 2 提示待实现；不能作为训练成功的依据。配置路径统一相对 `ml/`，后续读取器须基于配置文件位置解析，避免依赖启动目录。

## 与现有代码的关系

- `frontend/` 和 `frontend/handwriting-collector-mobile/` 继续负责采集，`deploy/` 负责部署。
- `backend/app/services/handwriting/features.py` 是线上特征实现，后端接口和测试仍引用它，保留原位；离线特征实现需明确输入格式后再实现或提取共享逻辑。
- `research/ai/` 保存现有 Prompt、工作流、知识库、工具契约和模拟评测；`research/data/` 保存沙盘字典及合成示例，继续服务现有功能。
- 本地 `database/emothaw/` 已迁至 `ml/data/raw/emothaw/`，不更改其文件内容。

## 环境与下一步

使用独立 Python 3.10 环境，勿复用后端 Python 3.12 环境。在 `ml/` 下创建 `.venv`，按 CPU/CUDA 环境安装 PyTorch，再安装 `requirements.txt`。依赖尚未验证，首次训练环境验证后再锁定版本。

先实现 MindTrace JSON 读取、质检、轨迹转换、统计特征及合成样例测试，再实现公开数据适配和训练。此次不改变采集协议、问卷或标签定义，方案正文作为研究参考材料保存。

原始数据、问卷、参与者映射、划分、模型及逐人结果不能提交；目录通过 `.gitkeep` 保留。提交前检查 `git status` 和暂存文件。忽略规则不能代替备份或访问控制。
