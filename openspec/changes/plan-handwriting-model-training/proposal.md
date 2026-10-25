# Proposal

## Why

项目已经取得 OUHD-L 在线笔迹、EMOTHAW 镜像与 Quick, Draw! 子集，但当前分支尚无可执行离线训练管线。CASIA-onDo 暂不可得，需要将原方案转换为可以逐步验收、明确替代数据来源并防止参与者泄漏的研发规划。

## What Changes

- 在独立 `ml/` 工作区规划统一轨迹、质检、特征、训练、评估与推理交付，不让线上服务依赖训练环境。
- 阶段 A 暂用 OUHD-L 自监督预训练 BiGRU，保留未来 CASIA-onDo 的独立实验入口，不混用数据集名称和结果。
- 阶段 B 使用经核验与授权确认的 EMOTHAW 开展传统基线、从零训练、冻结迁移与局部微调对照。
- 阶段 C 使用 MindTrace 自采数据训练独立 MRS-18 回归头，开展参与者隔离验证、消融与纵向关联分析。
- 规定实验可复现、数据权限、非诊断输出和模型接入门槛；待定需求集中登记，依赖明确前继续不受影响的工作。
- 本次仅建立规划和拟新增能力规格，不实现模型、修改采集协议或启用线上预测。

## Capabilities

### New Capabilities

- `trajectory-data-pipeline`：数据来源与权限登记、统一轨迹、质检、特征、参与者划分和私有数据隔离。
- `handwriting-model-training`：自监督、监督与目标域迁移，实验追溯、基线和独立评估。
- `research-inference`：模型包兼容性、质量门控、结构化研究输出及解释边界。

### Modified Capabilities

无；仓库此前没有 OpenSpec 正式能力规格。

## Impact

未来实现集中在 `ml/`，按需修改 `.gitignore` 和测试；推理通过明确接口接入后端，保留现有 LlmGateway 边界。训练拟用独立 Python 3.10、PyTorch、NumPy、Pandas、SciPy、scikit-learn，安装版本与 CUDA 组合在环境实测后锁定，不复用后端环境。当前只提交 `openspec/` 内文本，不提交数据、权重、缓存、问卷或个人结果。
