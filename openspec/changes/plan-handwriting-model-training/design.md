# Design

## Context

2026-10-25 本地基线：OUHD-L core 有 2,403 条 CSV 和 2,403 张图，311 名书写者；train/val/test 为 1,911/239/253 条和 248/31/32 人，writer_id 无交叉。全量关键通道扫描读取约 37,508,288 点，无非有限值、时间倒序或非法笔状态；258 个文件有重复时间戳。每条 4,607–61,387 点，文件内时间差中位数均为 2ms，压力观测范围 0–4095。扫描不是语义正确或跨设备可比的保证。授权以随包 LICENSE 与来源核验为准，本地数据卡声明 CC BY 4.0。

EMOTHAW 镜像目录有 913 条 SVC；既有核验记录为 129 名参与者与 129 条标签，以 Directory + File Number user 关联。已有记录提示 7 组相同内容、1 个点数不符文件、2 个时间倒序文件以及修正/缺任务说明；实施前重核，不能把旧目录与镜像重复读入。官方版本与镜像许可确认尚未完成。

Quick, Draw! 既有记录为 345 类、50,156 条轨迹，无笔压、心理标签或可靠参与者 ID，仅作可选辅助。当前 raw 目录未发现 MindTrace 数据。CASIA-onDo 未取得。moyi/main 尚无此前 LLM-Study 的训练骨架。当前命令解析到 Python 3.10，未安装 torch；GPU 为 RTX 4060 Laptop，约 8GB 显存，驱动 551.76，CUDA 可用性仍须安装后实测。

## Goals / Non-Goals

目标是验证公开在线笔迹预训练是否改善少量中文笔迹的问卷指标预测，并交付可复现实验、可解释特征和受门控推理。模型为 BiGRU，不训练或微调语言大模型，不做 OCR，不保证预训练必然获益，不输出诊断或未经定义的心理健康百分比。既有产品各模块继续运行，本变更不重建聊天、手账、沙盘或采集端。

## Decisions

### 1. 主路线与条件分支

主线：OUHD-L 统一轨迹 → 遮盖重建编码器 → EMOTHAW 基线与迁移对照 → MindTrace 新回归头与独立验证 → 研究推理包。

OUHD-L 使用乌尔都语，设备、采样率、坐标系和中文目标域不同；其预训练效果属于跨语言、跨设备迁移假设。CASIA 到位后新增独立来源、划分和运行记录，与 OUHD-L 做可比实验，保留已有结果；是否取代主线由实际比较决定。Quick, Draw! 默认不加入主训练，若启用必须显式缺失掩码并单列实验，不能借类别标签生成心理标签。

EMOTHAW 权限或标签未确认期间，只推进允许的数据清点、适配测试、OUHD-L 实验和合成标签测试，不产出正式 EMOTHAW 监督结论。若最终不能使用，则跳过阶段 B，以 OUHD-L 编码器和有效 MindTrace 标签开展探索性迁移，并如实记录公开监督阶段缺失。MindTrace 不足时继续数据管线和预训练，不能复制样本补人数。

### 2. 目标目录（未来实现，不代表已创建）

```text
ml/
  README.md
  requirements.txt                 # 验证后锁定；torch 安装配置另记
  configs/{data,pretrain,emothaw,mindtrace}.yaml
  data/
    raw/{ouhd_l,casia_ondo,emothaw,mindtrace,quickdraw}/
    processed/                     # 私有派生轨迹与特征
    splits/                        # 私有参与者划分
  src/
    datasets/{ouhd_l,casia,emothaw,mindtrace}.py
    preprocessing/{quality_control,trajectory,features}.py
    models/{bigru_encoder,reconstruction_head,prediction_head}.py
    training/{pretrain,supervised,transfer}.py
    evaluation/{metrics,cross_validation}.py
    inference/{bundle,predict}.py
  scripts/
    00_inventory.py
    01_prepare_data.py
    02_extract_features.py
    03_train_baselines.py
    04_pretrain.py                 # 数据源参数化，默认 ouhd_l
    05_train_emothaw.py
    06_transfer_mindtrace.py
    07_evaluate.py
  tests/                           # 仅合成样例，不放参与者原始记录
  checkpoints/
  experiments/
  reports/
```

数据、划分、模型、逐人日志和报告目录默认忽略；只允许显式白名单的无敏感信息 README/占位文件。`ml/.venv/` 独立于后端；不得删除或重命名已有下载文件。OpenSpec 记录公开汇总与方案，源轨迹和身份映射保留受控本地存储并备份。

### 3. 统一数据契约与质检

每个任务包含 schema_version、dataset/version、source_id/hash、匿名 participant_id、session_id、task_id、device_profile、原始尺寸/单位、五通道轨迹、逐点逐通道 feature_mask、笔画边界、quality 标记、label/instrument/version/validity。缺失字段显式标记，不把未知压力当真实零。统一时间为秒；从原始 X/Y/Time 计算增量，不默认相信预计算速度和 dt。

OUHD-L 使用 writer_id 作为分组键，保留官方划分。保留原坐标、笔压统计与归一化参数；不同设备不能仅以各自最大观测压力除法便声称物理可比。重复时间点默认在派生副本中保留文件顺序并合并相同时间/相同笔状态的连续点（位置与压力取均值），发生笔状态转换的同刻事件保留但标记零 dt、速度无效；输出修复计数。时间倒序、无法解析的单位或笔状态冲突进入隔离/复核，不自动排序掩盖问题。最终策略经重复时间戳审查确认后冻结版本。

长轨迹先按参与者划分，再切窗；首版窗口 256 点、不跨参与者或原始记录，不把各窗计作独立人次。保留窗口起止索引、真实时间间隔及边界信息。500Hz 下 256 点仅约 0.512 秒，因此 256/512/1024 点或重采样可作为验证集上的后续实验，不能依据测试集选择。仅在 train 或当前交叉验证训练折拟合归一化、插补、特征筛选与采样策略。

特征首版约 20–30 维：速度、加速度、压力、停顿、轨迹长度/方向/直线度、包围盒与重复抄写一致性。停顿阈值与尺寸校准写入配置；单位不明时不报告物理速度。MindTrace 解析特别核验 yNorm 首点差异、反向计分、symptomSumS 与 rapid_response_pattern；质量待复核标签不参与监督。EMOTHAW 按复合键连接，不依赖文件名或 CSV 行顺序。

### 4. 模型与训练默认值

BiGRU 两层，单方向 hidden=64，双向表示 128 维，dropout=0.2。五个观测通道与 feature_mask、遮盖标志分别建模，编码器实际输入维度须在实现时明确并写入模型元数据，不能只因“五通道”便固定总输入维度为 5。padding 不参与池化或损失。

自监督：连续片段遮盖约 15% 有效点，恢复 dx/dy/dt/pressure；只在遮盖且真实有效的通道计算 Huber，标准化后通道权重初始均为 1。不泄漏被遮盖目标；mask、missing 与 padding 必须区分。AdamW，lr=0.001，batch=32，最多 50 epoch，验证损失连续 7 轮无改善早停，seed=42。显存不足只调整 batch/梯度累积并记录，不默默截断数据。预训练测试报告 masked MAE/Huber，低损失不视作心理预测有效。

监督：先冻结编码器训练小头，再比较低学习率局部解冻；池化多个窗口为任务表示，再按参与者/轮次聚合。统计特征融合为独立消融。EMOTHAW 按三维 DASS 的已核实标签分别评价；阈值未知不二分，连续分数只有在版本与语义核实后才可回归。MindTrace 移除 DASS 头，主要预测 MRS-18 symptomSumS（0–64，计分需由数据契约确认），维度分数和纵向变化是次要探索目标。

### 5. 对照实验与评估

| 编号 | 实验 | 主要比较 |
| --- | --- | --- |
| EXP-00 | MindTrace Dummy 回归 | 简单均值误差 |
| EXP-01 | MindTrace 人工特征 + Ridge / Random Forest | 可解释基线 |
| EXP-02 | EMOTHAW Dummy + Logistic Regression / Random Forest，或已登记回归版本 | 公开监督基线 |
| EXP-03 | EMOTHAW 从零 BiGRU | 无预训练对照 |
| EXP-04 | OUHD-L 预训练后冻结编码器 → EMOTHAW | 对比 EXP-03 |
| EXP-05 | OUHD-L 预训练后局部微调 → EMOTHAW | 对比 EXP-04 |
| EXP-06 | 候选编码器 + MindTrace 新回归头 | 目标域迁移 |
| EXP-07 | 最佳编码器 + 统计特征融合 | 对比 EXP-01/06 |
| EXP-08 | 去掉压力、速度、形状等输入及训练标签置乱 | 消融与泄漏排查 |

EXP 编号刻意与原方案 E0–E7 区分；所有结果记录真实数据源。EMOTHAW 默认外层 5 折参与者分组验证、内层参与者分组选择参数，类别太少时报告不可估计或登记调整，不能让同一个人跨集合。分类报告 Macro-F1、balanced accuracy、各类召回和混淆矩阵；回归报告 MAE、RMSE、Spearman。与旧论文划分不同不声称严格复现。

MindTrace 同人同轮为一个监督样本，两次标准抄写为主，热身/自由书写作可选分支。主评估 LOSO，内层参与者分组选择参数与早停；同人多轮全部在同一外层折。任何目标域无标签预训练也必须排除外层测试参与者。比较模型使用一致外层划分与计算预算，最终对照建议 3 个固定种子；按人汇总误差及参与者级 bootstrap 不确定性，样本不足不能声称稳定临床泛化。LOSO 测试预测不得用于反复选“最佳”架构，确认性结论需冻结协议或后续独立队列。

纵向分析使用同人相对首轮的特征/分数差值，单独报告关联与缺测，不能与新参与者预测混算或宣称因果。

### 6. 可复现产物与接入

每次 run 保存 run_id、代码提交、配置/Schema/预处理版本、数据清单哈希、来源和授权状态、划分、种子、环境锁定、CPU/CUDA 与显存、训练历史、最佳 epoch、指标和异常摘要。哈希与个人清单只保存在受控实验目录。推理包携带权重、输入维度/通道、标准化参数、特征顺序、目标量表/分数范围、模型与质量规则版本以及验证状态；不兼容输入必须拒绝，禁止静默对齐。

输出分开列出 data_quality、handwriting_features、questionnaire、model（prediction_status、predicted_mrs_score、version、limitations）。轨迹不合格、模型未验收或输入不兼容时 score=null，并返回原因；问卷复核状态独立呈现，不能作为预测输入。通过预设验证标准且经研究负责人确认后才启用个人估计；阈值未决定前只展示测量与研究汇总。置信区间与单人预测区间不同，未校准不生成“焦虑概率”。

后端仅接入独立推理服务或经过依赖审查的包，不导入训练目录。语言模型若后续启用，只解释经审核、获授权的最小化结构数据，不接收原始自由书写与身份，不修改分数；现有 LlmGateway 继续负责调用与降级。部署、训练、正式真人采集均不由本次文档提交自动触发。

## Risks / Trade-offs

跨语言/设备域偏移、短窗上下文不足、原始单位不明和压力校准会限制迁移；用从零对照、可复现消融和原始统计检验，不能预设收益。约 20 人 × 3 轮最多约 60 人次，有效人数可能更少；轻量头、分组验证和不确定性优先，模型失败也是结论。EMOTHAW 来源、量表规则和 MindTrace 采集批准未定时仅阻塞对应实验，不阻塞独立开发。

## Migration Plan

先保护本地数据与环境，再逐个实现适配/质检/特征，建立传统基线，再开展预训练与迁移，最后验证和接入。每阶段完成才勾选任务；失败记录原因、保留上一可用产物，不覆盖原数据。未来获得 CASIA 或新增量表均使用新数据/实验版本，不回写历史结果。

## Open Questions

所有待决定项及默认值集中见 [decisions.md](decisions.md)。默认值允许编写程序与合成测试，不能代替授权、标签核实或模型上线验收。
