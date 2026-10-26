# MindTrace 模型研发规划

本目录是离线笔迹模型研发的 OpenSpec 入口。当前变更为 [`plan-handwriting-model-training`](changes/plan-handwriting-model-training/proposal.md)，状态为规划完成、实现待开始。`specs/` 为未来归档后的正式能力基线，目前不预先归档尚未实现的能力。

先看 [训练流程](changes/plan-handwriting-model-training/training-flow.md)，再按实施任务逐步推进。

## 阅读顺序

1. [proposal.md](changes/plan-handwriting-model-training/proposal.md)：范围、目标和能力边界。
2. [design.md](changes/plan-handwriting-model-training/design.md)：整体路线、目录、数据契约、实验与交付门槛。
3. [tasks.md](changes/plan-handwriting-model-training/tasks.md)：分阶段实施清单与验收。
4. [decisions.md](changes/plan-handwriting-model-training/decisions.md)：已确认决策及执行边界。
5. `changes/plan-handwriting-model-training/specs/*/spec.md`：可验证的行为要求。

从 tasks 的阶段 1 开始，逐个交付。文档生成并不表示任务已经执行、数据已经获授权或模型已经通过验证。

## 依据与边界

- 原方案：`MindTrace Campus：从零开始的完整模型训练与迁移学习方案.md`，Git 参考 `2197891` 的 `docs/05-ai/` 同名文件；当前 moyi/main 没有该文件，不复制其历史代码骨架。
- 现行采集规范：[笔迹数据集与数位板采集规范](../docs/03-data/handwriting-collection-and-dataset-spec.md)。该规范中的旧数据分层 E0/E1/E2 与本变更的实验编号 EXP-00 等是不同概念。
- 项目 AI 边界：[AI 与多模态分析设计](../docs/05-ai/README.md)。
- 2026-10-25 本地检查与前一轮轨迹全量扫描结果作为规划输入；数据数量不是永久常量，正式运行必须重新生成清单。
- “训练大模型”在本规划中特指可预训练、迁移的小型 BiGRU 笔迹时序模型；本变更不需要语言模型训练或报告生成。

## 维护和校验

使用 `openspec validate plan-handwriting-model-training --strict --no-interactive` 校验。后续改变预测目标、数据划分、许可状态或实验协议时同步修改 proposal、design、specs、tasks 和决策记录。实施完成、检查通过后才归档变更。

原始数据与逐人结果不放入 OpenSpec；仅保留不含个人信息的规范和汇总。当前分支的 `ml/` 本地数据尚未受到该分支忽略规则的完整保护，实施前必须补齐忽略并验证；不得批量暂存整个工作区。

2026-10-25 负责人已确认13项决定：WHO-5为主目标、OUHD-L为正式预训练源，三条展示门槛见design，完整记录见decisions。模型截止2027年1月，整体项目截止2027年4月；本变更不含语言模型训练或报告生成。

2026-10-26 Q03按负责人接受的1A/2A/3A更新，见 [阶段性核验与执行决定](changes/plan-handwriting-model-training/q03-review.md)：先复核冻结现有探索，正式条件齐备后优先连续回归，分类不列必做。
