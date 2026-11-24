# 手写笔迹情绪分类：训练准备与执行手册

本目录是**独立于已冻结的 OUHD-L/WHO-5 回归管线**的新实验区。它读取采集端上传的 session JSON（`attempts[].points`，可选 `attempts[].image`），目标是把笔迹轨迹分类到一个小而可靠的情绪标签体系。

> 这不是诊断模型。笔迹不能单独证明一个人的情绪或心理疾病；所有个人级输出都必须经过参与者分组验证、校准和伦理审核。

## 1. 先看数据现实

在选模型之前，先回答三个问题：

1. 有多少**独立参与者**？不是多少 JSON、多少 attempt。
2. 有多少**人工标注**？每个情绪类多少条？标注者一致性如何？
3. 标签是**每个 session 一个**，还是每个 attempt 一个？

经验下限：

| 标注量 | 能做什么 | 不要做什么 |
|---|---|---|
| < 30 条 | 人工规则、LLM 辅助预标注、主动学习选样 | 不要训深度模型 |
| 30–100 条 | 手工特征 + 逻辑回归 / 随机森林；冻结编码器 + 线性头 | 不要报“泛化准确率” |
| 100–500 条 | SetFit/线性头、浅层 BiGRU、半监督自训练 | 不要随机拆分 attempt |
| 500+ 条、30+ 参与者 | BiGRU/1D CNN 微调、FixMatch/Mean Teacher | 不要用测试参与者的无标签数据做 transductive 训练 |

当前项目规划是 20 人 × 3 轮 ≈ 60 人次。对 6 类情绪分类，这仍然很小；**先把目标定为“探索性、可复现的基线”**，不要承诺高准确率。

> 2026-11-22 对服务器现有数据的分析结论：15 个真实 session、15 名参与者、0 条情绪标签、0 张图片；7 个旧 18 题 session 中只有 1 条可用分数。WHO-5 弱标签代理的 8 人留一参与者结果虽然看起来较高，但一个只看 `partial_record` 的规则就能达到同样准确率，属于采集质量混杂。详见 [server-dataset-analysis-2026-11-22.md](docs/server-dataset-analysis-2026-11-22.md)。当前不应训练或展示情绪模型。

## 2. 目录与数据流

```text
采集端上传 (uploads/日期/*.json)
        │  只读复制，不修改原始文件
        ▼
ml/emotion/data/raw/                  # 私有，git-ignored
        │  01_inventory.py            # 只读清单，不打印正文
        ▼
ml/emotion/data/inventory.json        # 私有
        │  02_build_manifest.py       # attempt 一行；标签可空
        ▼
ml/emotion/data/manifest.csv          # 私有
        │  03_train_baseline.py       # 手工特征基线
        │  04_train_sequence.py       # BiGRU（可加载 OUHD-L 编码器）
        ▼
ml/emotion/runs/<run-id>/             # 私有：指标、预测、检查点
```

`ml/emotion/data`、`models`、`runs`、`labels` 已在 `.gitignore` 中排除。**不要把 session JSON、标签 CSV、参与者 ID、图片或检查点提交到 Git。**

## 3. 环境

使用现有 `ml/.venv`（Python 3.10，PyTorch 2.6 CUDA）：

```powershell
ml/.venv/Scripts/python.exe -m pip install -r ml/emotion/requirements.txt
```

如果 `ml/.venv` 不存在，先按 [ml/README.md](../README.md) 创建并安装 `ml/requirements.txt`。

## 4. 第一步：把服务器数据复制到私有目录

在服务器上或通过受控 SMB/RDP 通道，把 `C:\yyh_project\mindtrace-collector\uploads` 复制到本机：

```powershell
# 示例：只读复制；目标目录不要放进 Git
robocopy "\\82.157.132.139\C$\yyh_project\mindtrace-collector\uploads" `
  "D:\private\mindtrace-emotion\raw" /E /COPY:DAT /R:1 /W:1
```

不要直接在服务器上传目录上训练；不要修改原始 JSON。`server` 端现在会把图片嵌在 JSON 的 `attempts[].image.dataUrl` 里，训练不需要先解码图片；只有做图像分支时才离线提取。

## 5. 第二步：只读清单

```powershell
ml/.venv/Scripts/python.exe ml/emotion/scripts/01_inventory.py `
  --input "D:\private\mindtrace-emotion\raw" `
  --labels "D:\private\mindtrace-emotion\labels\labels.csv"
```

输出 `ml/emotion/data/inventory.json`（私有）。终端只打印汇总：schema 分布、participants、sessions、attempts、图片数量/估算大小、质量状态、标签覆盖。它不会打印轨迹、问卷答案或参与者文件名。

先看这几个数：

- `participants` 太小（< 10）→ 只能做管线验证。
- `attempts` 多但 `participants` 少 → 不能证明泛化。
- `dataset_eligibility` 大量 `pending_quality_review` → 先做人工质量复核，不要直接当训练标签。
- `attempt_quality` 大量 `partial/invalid` → 先修采集或过滤。

## 6. 第三步：标签文件

标签是私有的 CSV，建议放在 `D:\private\mindtrace-emotion\labels\labels.csv`，列如下：

```csv
session_id,attempt_id,participant_id,emotion,label_source,confidence,annotator,notes
MT-24-XXXX-T001-...,,,neutral,manual,0.95,A01,
MT-24-YYYY-T001-...,,,anxiety,manual,0.80,A02,边界样本，已仲裁
MT-24-ZZZZ-T001-...,MT-...-COPY_SENTENCE_REPEAT_1-2,,sadness,manual,0.90,A01,attempt 级标签
```

- `emotion` 使用 `neutral / positive / sadness / anxiety / anger / other`；也接受 `happy/joy/relaxed/depress/worried/fear/angry` 等别名（见 `labels.py`）。
- `attempt_id` 为空时，标签作用于整个 session 的所有 attempt；非空时只作用于该 attempt。
- `label_source` 默认 `manual`；弱标签请明确写 `weak_mood_stress`、`weak_who5`、`weak_journal`、`pseudo`，训练脚本默认只使用 `manual`。
- 空 `emotion` 表示未标注，不是负类。
- 不要提交到 Git；不要写姓名、学号、联系方式。

标注建议：

1. 先写 1 页 codebook，定义每个类的边界和例子；允许 `other` 和“不确定”。
2. 至少 20% 样本双人标注，计算 Cohen's κ；κ 低时先改 codebook/合并类别，不要硬训。
3. 标注者不要看模型预测，也不要看 WHO-5 分数，避免锚定。
4. 保存 `annotator`、`confidence`、`annotated_at`，便于审计。
5. 标签文件按参与者分组划分；测试参与者绝不参与伪标签/主动学习选样。

## 7. 第四步：生成 manifest

```powershell
ml/.venv/Scripts/python.exe ml/emotion/scripts/02_build_manifest.py `
  --input "D:\private\mindtrace-emotion\raw" `
  --labels "D:\private\mindtrace-emotion\labels\labels.csv" `
  --output "ml/emotion/data/manifest.csv" `
  --require-usable
```

输出 `manifest.csv` 和 `manifest.summary.json`（私有）。一行一个 attempt，包含：

- 元数据：session/participant/attempt/task/quality/schema/source_path；
- 标签：`emotion/label_source/label_confidence/annotator`（可空）；
- 特征：`emotion-features-v0.1` 的 25 维手工特征；
- `split`：按 participant 的确定性 train/val/test 建议（训练脚本仍用分组 CV，不依赖这一列）。

如果只想先跑无标签自监督/管线检查，可以省略 `--labels`，所有 `emotion` 为空。

## 8. 第五步：先跑手工特征基线

```powershell
ml/.venv/Scripts/python.exe ml/emotion/scripts/03_train_baseline.py `
  --manifest ml/emotion/data/manifest.csv `
  --cv group5 `
  --model logreg
```

输出在 `ml/emotion/runs/baseline-<时间>/`：

- `metrics.json`：每个 fold、pooled 指标、dummy 基线、混淆矩阵；
- `predictions.csv`：逐 attempt 预测（私有）；
- `model.joblib`：最终全量模型（私有）；
- `model-card.md`：数据量、指标、局限。

可选：

```powershell
# 留一参与者，适合小样本，但会有 N 次训练
--cv loso
# 加入未标注数据做自训练（SelfTrainingClassifier，阈值 0.9）
--semi-supervised
# 加入弱标签（默认只用 manual）
--include-weak
```

**判断标准**：如果 logreg 的 macro-F1 不高于 dummy，先不要上深模型；检查标签质量、特征、任务差异和参与者泄漏。

## 9. 第六步：BiGRU 序列模型

### 9.1 从零训练

```powershell
ml/.venv/Scripts/python.exe ml/emotion/scripts/04_train_sequence.py `
  --manifest ml/emotion/data/manifest.csv `
  --data-root "D:\private\mindtrace-emotion\raw" `
  --cv group5 `
  --epochs 60 `
  --batch-size 16 `
  --lr 0.001
```

输入是每次 attempt 的 5 通道序列（dx、dy、dt 秒、pressure、pen_state）+ feature_mask + stroke_boundary，按时间重采样到 512 点；模型是 2 层双向 GRU（每方向 hidden=64，表示 128），dropout 0.2，attention/mean pooling 后接分类头。

### 9.2 加载 OUHD-L 自监督编码器

如果已有 `ml/experiments/pretraining/ouhd-formal-v1/encoder.pt`（见 [pretraining.md](../docs/pretraining.md)）：

```powershell
ml/.venv/Scripts/python.exe ml/emotion/scripts/04_train_sequence.py `
  --manifest ml/emotion/data/manifest.csv `
  --data-root "D:\private\mindtrace-emotion\raw" `
  --pretrained-encoder "ml/experiments/pretraining/ouhd-formal-v1/encoder.pt" `
  --freeze-encoder-epochs 5 `
  --lr 0.0003 `
  --cv group5
```

前 5 个 epoch 冻结编码器，只训练分类头；之后用较低学习率解冻。OUHD-L 是乌尔都语、不同设备和采样率，**跨域收益不是必然的**；必须与从零训练使用相同 fold、相同预算对照。

> 当前工作区的 `ml/data` 和 `ml/experiments` 是空的；如果找不到 `encoder.pt`，需要先按 `ml/README.md` 准备 OUHD-L 数据并运行 `04_pretrain.py`，或从受控备份恢复。

## 10. 模型怎么选

| 场景 | 首选 | 理由 |
|---|---|---|
| 标签 < 100，特征可解释 | 手工特征 + 逻辑回归/随机森林 | 稳定、快、能定位标签问题 |
| 标签 100–300，已有 OUHD-L 编码器 | 冻结 BiGRU 编码器 + 线性头 | 小样本下比全量微调稳 |
| 标签 300+，30+ 参与者 | BiGRU 微调 / 1D CNN | 能学时序动态 |
| 无标签数据很多、标签很少 | 自监督预训练 + 半监督（FixMatch/Mean Teacher） + 主动学习 | 利用无标签数据，但必须做消融 |
| 有自由书写图片/文本 | 文本/OCR 分支优先，笔迹为辅助 | 文本信号远强于纯笔迹；多模态融合需缺失模态 mask |

**不要**一上来找“笔迹情绪大模型”下载：目前没有可靠的、可直接用于中文手写轨迹情绪分类的公开预训练权重。真正可用的是：

- 本项目自己的 OUHD-L 掩码重建编码器（推荐）；
- 公开手写识别/图像模型（如 TrOCR、ResNet）只能做视觉/OCR 辅助，不是情绪模型；
- 公开情绪文本模型（CPED/GoEmotions）不适用于轨迹，除非做文本分支。

## 11. 模型/数据怎么下载

### 11.1 OUHD-L 数据

来源和许可见 [ml/configs/data.json](../configs/data.json)：`https://doi.org/10.5281/zenodo.20642162`。下载到 `ml/data/raw/ouhd_l/`，保留 `LICENSE` 和 `SOURCE.md`。如果 Zenodo 被网络限制，使用学校网络/VPN。

### 11.2 PyTorch 预训练图像模型（可选）

```python
import torchvision.models as models
weights = models.ResNet18_Weights.DEFAULT
model = models.resnet18(weights=weights)  # 自动下载到 ~/.cache/torch/hub/checkpoints
```

### 11.3 HuggingFace 模型（可选，文本/OCR 分支）

```powershell
python -m pip install huggingface_hub
huggingface-cli download <org>/<model> --local-dir D:\private\models\<model>
# 国内网络可设置镜像：
$env:HF_ENDPOINT = "https://hf-mirror.com"
```

不要把下载的权重提交到 Git；放在 `D:\private\models` 或 `ml/emotion/models`（git-ignored）。

## 12. 半监督与弱标签：怎么用才不骗自己

1. **先有手工基线**，再谈半监督。没有基线就无法判断伪标签是否带来收益。
2. `03_train_baseline.py --semi-supervised` 用 `SelfTrainingClassifier`：只用训练参与者的未标注 attempt，阈值 0.9；测试参与者绝不参与。
3. 序列模型的 FixMatch/Mean Teacher 需要更多无标签数据和更稳的教师；当前先不要默认开启，等基线稳定后再加。
4. 弱标签：
   - `mood`/`stress` 1–5 → valence/arousal 象限（见 `labels.py`），只作辅助目标，不作金标签；
   - WHO-5 低幸福感 → 辅助二分类，不是情绪类别；
   - 手账的 `emotion` 字段 → 弱标签，缺失不是负类；
   - 伪标签 → 只用于训练，不用于评估。
5. 必须做消融：仅 manual / +未标注自训练 / +弱标签 / +预训练编码器。每一组都用相同 participant folds。

## 13. 评估与验收

- 主指标：**macro-F1**；辅以 balanced accuracy、逐类 recall、混淆矩阵、ECE。
- 主验证：**参与者分组**（LOSO 或 GroupKFold）。随机按 attempt 拆分会被同一人的重复笔迹泄漏，指标不可信。
- 报告每个 fold、mean±std、pooled；不要只挑最好 seed。
- 做 label-scaling：每类 8/16/32/64/128 条，观察曲线。
- 负对照：打乱标签、随机伪标签、只用 dummy；异常高分先排查泄漏。
- 标签一致性上限：如果模型接近标注者 κ 对应的上限，继续加标签的收益有限。
- 未达到预登记门槛，不接入产品，不输出个人情绪概率。

## 14. 训练好的模型要不要上传 GitHub？

**代码、配置、模型卡：可以提交。**
**原始数据、标签 CSV、参与者信息、图片、检查点、运行目录：不要提交。**

权重建议：

| 方式 | 适用 | 注意 |
|---|---|---|
| GitHub Releases | 最终推理权重（单个 < 2GB） | 只放推理权重；附 SHA256、配置、指标、模型卡 |
| Git LFS | 团队私有仓库、需要版本化 | 会占 LFS 配额；不要把数据和权重混在一起 |
| HuggingFace 私有仓库 | 需要版本化/共享 | 设为 private；不要上传参与者数据；模型卡写限制 |
| 受控网盘/学校存储 | 含敏感数据或内部研究 | 最稳妥；Git 只放下载说明和校验和 |

无论哪种方式，上传前确认：

1. 权重不包含原始数据、路径、参与者 ID 或标签明细；
2. 训练数据同意书覆盖“模型开发”，且允许导出模型；
3. 附 `model-card.md`：taxonomy、数据版本、participant 数、指标、失败模式、非诊断声明；
4. 附 SHA256 和加载代码版本；
5. 如果模型可能记忆敏感文本/图片，按敏感资产处理，不公开。

仓库已有 `ml/**/*.pt` 等忽略规则；保持它。**不要**为了“方便”把 `ml/emotion/runs`、`ml/emotion/data`、`ml/emotion/labels` 加进 Git。

## 15. 现在最该做的三件事

1. **导出清单**：跑 `01_inventory.py`，确认参与者数、attempt 数、质量分布和已有标签数。
2. **定标签**：6 类 + 双人标注/仲裁；先标 100–200 条覆盖各类的样本。
3. **跑基线**：`02_build_manifest.py` → `03_train_baseline.py`；只有基线优于 dummy，才进入 BiGRU/半监督。

如果清单显示只有个位数参与者或每类个位数标签，当前的正确结论是“继续采集/标注”，而不是“换更复杂的模型”。

## 16. 已知限制

- 纯笔迹与情绪的关系证据弱，个体差异、设备、任务、疲劳、药物等混杂很多；不能做诊断或个体判断。
- 采集端的 schema 1.7 与图片字段仍在演进；训练前先核对 `schemaVersion` 和 `quality`。
- WHO-5 是两周幸福感，不是即时情绪；不能当情绪标签。
- 自由书写图片可能包含个人信息；OCR/标注/训练都要遵循同意范围和数据最小化。
