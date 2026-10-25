export type QuestionnaireScore = 0 | 1 | 2 | 3 | 4 | 5;
export type QuestionnaireDomain = "wellbeing";
export type QuestionnaireAnswer = QuestionnaireScore | null | undefined;

export type QuestionnaireItem = {
  id: string;
  number: number;
  domain: QuestionnaireDomain;
  domainLabel: string;
  text: string;
  scoringDirection: "direct" | "reverse";
};

// WHO-5 Chinese PR, September 2007; WHO 2024 scoring. Instrument adaptation:
// CC BY-NC-SA 3.0 IGO. Sources and decisions: docs/06-development/who5-questionnaire.md.
export const QUESTIONNAIRE_ID = "WHO_5";
export const QUESTIONNAIRE_VERSION = "zh-CN-2007/2024.1";
export const QUESTIONNAIRE_SOURCE = "https://www.who.int/publications/m/item/WHO-UCN-MSD-MHE-2024.01";
export const QUESTIONNAIRE_ITEM_SET_HASH = "sha256:652256190aa248fb66bb8804a92155bb47876b2e0cd70171070a60de7100dbe2";
export const SCORE_RULE_VERSION = "who5/2024-total-and-2007-item-screen-v1";
export const RESPONSE_OPTIONS = [
  { score: 5, label: "所有时间", days: "5 分" },
  { score: 4, label: "大部分时间", days: "4 分" },
  { score: 3, label: "超过一半的时间", days: "3 分" },
  { score: 2, label: "少于一半的时间", days: "2 分" },
  { score: 1, label: "有时候", days: "1 分" },
  { score: 0, label: "从未有过", days: "0 分" },
] as const satisfies readonly { score: QuestionnaireScore; label: string; days: string }[];

export const QUESTIONNAIRE_ITEMS: readonly QuestionnaireItem[] = [
  "我感觉快乐、心情舒畅",
  "我感觉宁静和放松",
  "我感觉充满活力、精力充沛",
  "我睡醒时感到清新、得到了足够休息",
  "我每天生活充满了有趣的事情",
].map((text, index) => ({ id: `WHO5_0${index + 1}`, number: index + 1,
  domain: "wellbeing", domainLabel: "心理幸福感", text, scoringDirection: "direct" }));

export function scoreQuestionnaireAnswer(_item: QuestionnaireItem, answer: QuestionnaireAnswer): QuestionnaireAnswer {
  return answer;
}

export function calculateQuestionnaireSummary(
  answers: readonly QuestionnaireAnswer[], consentAccepted = true, responseTimesMs: readonly number[] = [],
) {
  const validValue = (value: unknown): value is QuestionnaireScore => typeof value === "number" && Number.isInteger(value) && value >= 0 && value <= 5;
  const normalized = QUESTIONNAIRE_ITEMS.map((_, index) => answers[index]);
  const valid = answers.length <= 5 && normalized.every((value) => value == null || validValue(value));
  const answeredCount = normalized.filter(validValue).length;
  const resolvedCount = normalized.filter((value) => value !== undefined).length;
  const complete = valid && answeredCount === 5;
  const missingItemIds = QUESTIONNAIRE_ITEMS.filter((_, i) => normalized[i] === null).map((item) => item.id);
  const unansweredItemIds = QUESTIONNAIRE_ITEMS.filter((_, i) => normalized[i] === undefined).map((item) => item.id);
  const canScore = complete && consentAccepted;
  const rawTotal = canScore ? normalized.reduce<number>((sum, value) => sum + (value as number), 0) : null;
  const percentageScore = rawTotal === null ? null : rawTotal * 4;
  const lowItemIds = canScore ? QUESTIONNAIRE_ITEMS.filter((_, i) => (normalized[i] as number) <= 1).map((item) => item.id) : [];
  const belowCutoff = rawTotal === null ? null : rawTotal < 13;
  const needsFurtherAssessment = belowCutoff === null ? null : belowCutoff || lowItemIds.length > 0;
  const resultTitle = !canScore ? null : belowCutoff ? "近期心理幸福感偏低"
    : lowItemIds.length ? "总分未低于阈值，个别体验值得关注" : "本次未触发进一步评估提示";
  const recommendation = !canScore ? "请完成全部 5 题后查看评定；跳题不按零分处理。"
    : needsFurtherAssessment ? "建议联系学校心理咨询中心或专业人员进一步评估。量表提示不代表疾病诊断。"
      : "可继续保持有帮助的生活习惯。若持续感到困扰或日常生活受影响，仍可寻求专业支持。";
  const qcFlags: string[] = [];
  if (missingItemIds.length) qcFlags.push("missing_items");
  if (!valid) qcFlags.push("invalid_response_value");
  const validResponseTimes = responseTimesMs.filter((value) => Number.isFinite(value) && value >= 0);
  const fastResponseCount = validResponseTimes.filter((value) => value < 1000).length;
  // Collection heuristic only: never changes WHO-5 scores or interpretation.
  if (responseTimesMs.length === 5 && validResponseTimes.length === 5 && fastResponseCount >= 4) qcFlags.push("rapid_response_pattern");
  const recordStatus = !consentAccepted || !valid ? "excluded" : !complete
    ? resolvedCount === 5 || answeredCount > 0 ? "usable_partial" : "not_started"
    : qcFlags.includes("rapid_response_pattern") ? "review_required" : "usable_full";
  return {
    completionStatus: !valid ? "invalid" : complete ? "complete" : resolvedCount === 5 ? "complete_with_missing" : "incomplete",
    answeredCount, missingItemIds, unansweredItemIds,
    scoredItemValues: QUESTIONNAIRE_ITEMS.map((entry, i) => ({ questionId: entry.id, scoringDirection: entry.scoringDirection,
      rawScore: validValue(normalized[i]) ? normalized[i] : null, scoredScore: validValue(normalized[i]) ? normalized[i] : null })),
    rawTotal, percentageScore, belowCutoff, lowItemIds, needsFurtherAssessment, resultTitle, recommendation,
    scoreRuleVersion: SCORE_RULE_VERSION,
    responseTiming: { recordedItemCount: validResponseTimes.length,
      totalMs: Math.round(validResponseTimes.reduce((sum, value) => sum + value, 0) * 10) / 10,
      underOneSecondCount: fastResponseCount, qualityRule: "collection heuristic: review when at least 4 of 5 responses are under 1000 ms; not a WHO-5 validity rule" },
    quality: { recordStatus, qcFlags, exclusionReason: !consentAccepted ? "consent_not_granted" : !valid ? "invalid_response_value" : null,
      reviewedAt: null, reviewedBy: null },
  };
}

export function formatLocalDate(date: Date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}
