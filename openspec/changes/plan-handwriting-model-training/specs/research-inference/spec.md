# Spec Delta

## Purpose

为经验证的笔迹研究模型提供版本化推理契约和清晰的质量门控，使应用能够区分直接测量、问卷信息与模型估计，避免未验证结果被展示为个人心理诊断，同时保护原始书写与敏感研究信息。

## ADDED Requirements

### Requirement: 推理包显式校验兼容性
系统 SHALL 加载带有模型、输入通道、特征顺序、预处理、目标量表与验证状态的版本化推理包；MUST 拒绝不兼容输入，不静默猜测通道或使用其他量表预测头。

#### Scenario: 输入预处理版本不匹配
- **WHEN** 推理请求的 Schema 或特征版本与模型包不兼容
- **THEN** 返回明确失败原因且不产生分数，保留模型版本信息用于排查

### Requirement: 未满足条件不产生个人估计
系统 SHALL 在轨迹不合格、模型未通过预登记验收或三条展示门槛未全部通过时返回 prediction_status 和原因，predicted_who5_raw_total 与 predicted_who5_percentage MUST 为 null；问卷质量状态独立呈现且不得成为预测输入。

#### Scenario: 尚未通过展示验收
- **WHEN** 用户请求未获展示验收模型的个人结果
- **THEN** 仅返回允许展示的测量信息、模型不可用状态和局限，不返回个人问卷分数估计

### Requirement: 结果区分证据来源
系统 SHALL 分别输出 data_quality、handwriting_features、questionnaire 与 model，包含目标、版本、状态和局限；MUST 不将模型估计称为医学诊断，不生成未经校准的患病概率或未定义的健康百分比。

#### Scenario: 模型通过研究验收
- **WHEN** 合格轨迹经兼容且已验收模型完成预测
- **THEN** 结果明确标识为 WHO-5 幸福感总分估计（0–25），百分制为总分乘4且不是概率，并与实际问卷及直接测得特征分开展示

### Requirement: 三条展示门槛同时通过
系统 SHALL 仅在 LOSO MAE 较 Dummy 降低至少20%且不劣于预登记 Ridge/特征基线、参与者配对 bootstrap 改善量95%CI下界大于0、3种子至少2个方向一致且名义80%预测区间实测覆盖70–90%时允许个人预测展示；MUST 在外层训练参与者内校准区间，不能用测试结果调整。

#### Scenario: 稳定性或覆盖未达标
- **WHEN** 模型平均误差达标但种子稳定性或区间覆盖不达标
- **THEN** predicted_who5_raw_total 与 predicted_who5_percentage 均为 null，仅展示测量和研究汇总并说明未通过项

#### Scenario: 区分两种不确定性
- **WHEN** 执行最终展示验收
- **THEN** 分别核验参与者级改善量置信区间和个人预测区间覆盖，不使用MAE置信区间代替预测区间
