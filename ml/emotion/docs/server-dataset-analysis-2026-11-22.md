# 采集服务器数据集分析（2026-11-22）

本报告只使用聚合统计，不包含参与者姓名、逐人预测或原始轨迹。原始 JSON、弱标签表和运行产物都留在 git-ignored 私有目录。

## 结论摘要

**当前数据集不能训练手写笔迹情绪分类模型。** 原因不是模型不够复杂，而是：

1. **没有情绪标签。** 所有真实 session 只有问卷分数，没有 `emotion` 类别；人工标注数为 0。
2. **可用样本极少。** 15 个真实 session、15 名参与者、62 个 attempt；每人只有 1 次 session，无法做有意义的纵向或泛化验证。
3. **问卷标签本身大量缺失。** 7 个旧 18 题 session 中只有 1 个有可用的 `symptomSumS`；其余 6 个存在 `missing_items` 和/或 `rapid_response_pattern`。
4. **书写质量与弱标签高度混杂。** 8 个 WHO-5 session 中，3 个低于切点；其中 2 个 **0 个 usable attempt**。一个只用“是否 partial_record”的规则就能达到与模型相同的分类准确率，说明模型很可能在学采集质量，而不是幸福感/情绪。
5. **没有图片。** 现有 17 个 JSON 的 `attempts[].image` 全为空；它们都早于最新图片格式，当前服务端图片能力尚未被真实数据验证。

## 数据清单

| 项目 | 数值 |
|---|---:|
| JSON 文件 | 17 |
| 其中真实采集 | 15 |
| 其中 synthetic deployment test | 2（`excluded_test_record`，已排除） |
| 真实参与者 | 15 |
| 真实 session | 15（每人 1 次） |
| attempt | 62 |
| 总大小 | 约 44.5 MB |
| schema 1.6 / 1.7 / 1.8 | 8 / 2 / 7 |
| 图片 attempt | 0 |
| attempt 质量 usable / partial / unknown | 26 / 34 / 2 |
| datasetEligibility eligible / pending / partial / excluded | 4 / 7 / 4 / 2 |

## 标签现状

### 旧 18 题 MRS-18（7 个真实 session）

- 只有 1 个 session 有非空 `symptomSumS`（36）。
- 其余 6 个 `questionnaire.derived.symptomSumS` 为空，`qcFlags` 包含 `missing_items` 和/或 `rapid_response_pattern`。
- 结果：**1 条有效连续标签，无法训练分类或回归。**

### WHO-5（8 个真实 session）

| 指标 | 数值 |
|---|---:|
| 真实 WHO-5 session | 8 |
| 问卷 `recordStatus=usable_full` | 8 |
| `rawTotal` 范围 | 10–20 |
| 低于切点（<13） | 3 |
| 不低于切点 | 5 |
| eligible | 4（全部不低于切点） |
| partial_record | 4（3 个低于切点 + 1 个不低于） |

WHO-5 是**两周幸福感**，不是即时情绪，也不是诊断标签。即使有 8 条，也不能当作“情绪类别”。

### 书写质量

- 62 个 attempt 中只有 26 个 `usable`，34 个 `partial`。
- WHO-5 子集中：
  - 不低幸福感（label=0）的 usable attempt 数：4、4、4、4、3。
  - 低幸福感（label=1）的 usable attempt 数：0、0、3。
- 两个低幸福感 session 没有任何 usable attempt；特征来自 partial 轨迹。

## 已尝试的训练（弱标签代理，不是情绪分类）

由于没有情绪标签，只能用 WHO-5 的“低于切点”做一个**诊断性代理实验**，验证管线是否有信号。方法：

- 输入：每个 session 的两次标准抄写 attempt 的 25 维手工特征取平均，选 9 维（点数、时长、速度中位数/标准差、压力均值/标准差、包围盒面积、笔画间停顿数、笔画内 500ms 停顿数）。
- 模型：标准化 + 逻辑回归（C=0.5，class_weight=balanced）。
- 验证：留一参与者（8 折）。
- 对照：多数类 dummy；以及一个 **质量规则**（`partial_record` 判为低幸福感）。

### 结果

| 指标 | 逻辑回归 | 多数类 dummy | 质量规则 |
|---|---:|---:|---:|
| Accuracy | 0.875 | 0.625 | **0.875** |
| Macro-F1 | 0.855 | 0.385 | **0.873** |
| Balanced accuracy | 0.833 | — | — |

连续分数 Ridge：

| 指标 | 数值 |
|---|---:|
| Ridge 留一参与者 MAE | 3.81 |
| 训练均值基线 MAE | 4.00 |

精确标签置换（8 人、3 个阳性，共 C(8,3)=56 种标签分配）：

- 观察到 0.875 准确率的置换比例：**0.0536（3/56）**。
- 这不是显著证据；而且是在看到结果后做的探索性检验。

### 为什么这个结果不可信

1. **质量混杂**：一个不看笔迹特征、只看 `datasetEligibility == partial_record` 的规则，准确率和 F1 与模型几乎相同。模型很可能在学“这次采集是否 partial/可用”，而不是幸福感。
2. **标签与质量共线**：3 个低幸福感 session 中 2 个 0 个 usable attempt；5 个非低幸福感 session 中 4 个 eligible。
3. **样本量太小**：8 人、3 个阳性；一个人预测错就会改变 12.5% 的准确率。
4. **多重比较/特征选择**：9 个特征、多个指标、事后置换，不能当作确认性结果。
5. **目标不是情绪**：WHO-5 低幸福感 ≠ 某一种情绪类别；不能外推为“焦虑/悲伤分类器”。

### MRS-18 代理

- 只有 1 条有效 `symptomSumS`，脚本返回 `too_few_rows_or_classes`，没有训练。

## 服务端部署状态

- 最新接收器已部署到 `82.157.132.139` 的 `C:\yyh_project\mindtrace-collector`。
- `/health` 返回 `ok=true`，并暴露 `maxImageBytes=8388608`、`maxImageTotalBytes=16777216`、`maxImagesPerSession=12`、`requireImageConsent=false`。
- 用合成 `excluded_test_record` + 1 张 1×1 PNG 做了线上一轮验证：HTTP 200，`images=1`，`imageBytes=67`；测试文件随后已从服务器删除。
- `requireImageConsent=false` 是因为最新 main 客户端仍发送 `local-anonymous-collection-v1.2`；要开启严格图片同意，需要先把客户端 consent 版本/scope 升到 v1.3/v1.4。
- 现有 17 个 JSON 都没有图片，说明还没有真实数据走过新图片路径。

## 建议

1. **不要用当前数据训练或展示情绪模型。** 当前唯一可复现的结论是“管线和接收器工作，但数据不支持模型”。
2. **先修数据质量**：
   - 18 题问卷的 `missing_items`/`rapid_response_pattern` 必须解决；否则 6/7 旧 session 没有可用标签。
   - 低幸福感 session 的书写质量必须至少达到 usable；否则模型会学质量。
3. **定义情绪标注**：6 类（neutral/positive/sadness/anxiety/anger/other）codebook、双人标注、κ、仲裁。WHO-5 只做辅助/弱标签，不能当情绪金标签。
4. **扩大样本**：按规范目标至少 80 名参与者、每人多次；当前 15 人 × 1 次远不够。先以 30+ 参与者、每类 20+ 人工标签作为最低探索门槛。
5. **用主动学习提高标注效率**：先标覆盖各类的 100–200 条，再按 entropy/margin + 参与者多样性选下一批。
6. **新客户端上线后重新采集图片数据**，并验证服务端图片校验、同意版本和 manifest-v2；再决定是否做图像/OCR 分支。
7. **训练前预登记**：标签体系、分组划分、macro-F1、dummy/特征基线、标签缩放曲线、负对照和展示门槛。当前 OpenSpec 的 Q03 已关闭 EMOTHAW 分类；情绪分类应作为新的 `plan-emotion-classification` 变更单独预登记。

## 复现

```powershell
python -I ml/emotion/scripts/01_inventory.py --input ml/emotion/data/raw
python -I ml/emotion/scripts/05_weak_proxy.py --input ml/emotion/data/raw `
  --output-dir ml/emotion/runs/weak-proxy-real
```

私有产物：`ml/emotion/data/inventory.json`、`ml/emotion/runs/weak-proxy-real/`（`metrics.json`、`weak_labels.csv`、`predictions-*.csv`）。这些目录均被 Git 忽略。
