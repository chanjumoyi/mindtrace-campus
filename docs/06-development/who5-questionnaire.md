# WHO-5 量表实现与决策记录

## 来源

World Health Organization. The World Health Organization-Five Well-Being Index (WHO-5). Geneva: WHO; 2024. WHO/UCN/MSD/MHE/2024.1.

- [WHO 发布页与 2024 计分说明](https://www.who.int/publications/m/item/WHO-UCN-MSD-MHE-2024.01)
- [WHO 提供的 Chinese PR 中文原表（2007 年 9 月）](https://cdn.who.int/media/docs/default-source/mental-health/five-well-being-index-(who-5)/who5_chinese_pr.pdf)
- © WHO 2024. 量表内容及本项目的数字化量表改编遵循 [CC BY-NC-SA 3.0 IGO](https://creativecommons.org/licenses/by-nc-sa/3.0/igo/)，用于非商业研究。商业使用需向 WHO 确认许可。本项目不使用 WHO 标志、不暗示 WHO 背书。此说明不将其他独立代码改为该许可。

题干、顺序、六档时间频率和分值按官方中文原表录入；只移除印刷换行，改为逐题选择。itemSetHash 是按顺序以 LF 连接五个题干后的 UTF-8 SHA-256。

## 评定

共 5 题，每题 0–5 分，评估过去两周的心理幸福感；高分表示幸福感更好。原始总分 0–25，百分制 = 总分 × 4。百分制不是概率或人群百分位。

WHO 2024：原始分 <13（百分制 <50）提示幸福感偏低，建议进一步评估。边界为 12/48 与 13/52。中文原表另建议任一题为 0 或 1 时进一步评估；单独保存低分题列表，与总分阈值分开记录。总分较高但单题触发时不称为总分偏低。

结果不作疾病诊断，不自行分轻中重度；未触发提示不等于没有心理困扰。跳题、未答、非法值或未同意时不生成总分与评定，不按零分插补。书写完成后展示结果，不影响独立随机分配的抄写任务。

快速答题仅是采集质控：5 题有有效计时且至少 4 题少于 1 秒时人工复核；不是 WHO 规则，不改变分数。全部选相同答案不视为无效。

## 版本与兼容

session schema/app 为 1.7.0，questionnaire response 为 2.0.0，instrumentId 为 WHO_5。derived 保存 rawTotal、percentageScore、belowCutoff、lowItemIds、needsFurtherAssessment、规则版本和逐题分值。旧 18 题的症状及领域派生分不再输出；旧数据必须保留原量表身份，不与 WHO-5 混合作标签。研究规范中的 PHQ/PSS 方案未更改。

上传地址、令牌读取、请求头、超时、网页/原生上传、重试及管理员不上传规则保持原样。仓库没有对应接收服务源码，下游消费者可能需要按新版本适配。验证仅用合成记录和拦截请求，不上传测试资料。

## 本次取舍

1. 允许 20 题以内，选用完整的官方 5 题版本，不为凑题数自行拼题。
2. 当前状态按原量表定义为过去两周，未改成此刻情绪。
3. 2024 总分阈值与 2007 中文单题提示分别导出，共同用于进一步评估建议。
4. 用户本次明确指定 moyi 实现与本地提交，覆盖通用分支流程；不推送、不合并 main、不发布。
5. 响应结构递增版本，不伪装成旧量表兼容下游；上传连接配置保持不变。
