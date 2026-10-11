# 《笔迹心理学》知识接入规则

本书只作为笔迹特征假设和对话解释素材，不作为心理状态的真实标签来源。

每一条进入知识库的假设必须记录：PDF页码、原文摘要、可观测特征、适用任务、方向、置信度和验证状态。

`book_hypotheses_template.csv` 与 `book_hypotheses_v0.1.csv` 使用同一套列，顺序固定为：

```text
hypothesis_id, source_title, pdf_page, source_summary, observable_feature,
implementation_field, direction, task_scope, confidence, measurement_status,
evidence_status, safety_note
```

- `confidence`：只有经过独立验证才填写等级，书籍假设一律为 `unrated`；方法论原则填 `not_applicable`。
- `evidence_status`：书籍来源的统一填 `book_hypothesis_unvalidated`，流程原则填 `methodological_principle`。
- `measurement_status`：`available`＝已有字段可计算；`to_implement`＝特征尚未实现；`policy_available`＝属于流程约定。

模型输出分为三层：

1. 客观观察：压力、速度、停顿、倾角、布局等可复核数据。
2. 待验证主题：明确使用“可能”“值得进一步了解”等非确定措辞。
3. 探索问题：建议用户结合自评量表、近期情境或专业支持进一步确认。

禁止从单次笔迹直接输出人格定论、疾病诊断、危机等级或治疗建议。
