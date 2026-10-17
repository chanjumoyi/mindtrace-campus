export type QuestionnaireScore = 0 | 1 | 2 | 3 | 4;
export type QuestionnaireDomain = "mood_interest" | "worry_tension" | "stress_coping" | "sleep_energy_attention" | "daily_function";
export type QuestionnaireAnswer = QuestionnaireScore | null | undefined;

export type QuestionnaireItem = {
  id: string;
  number: number;
  domain: QuestionnaireDomain;
  domainLabel: string;
  text: string;
  scoringDirection: "direct" | "reverse";
};

export const QUESTIONNAIRE_ID = "MINDTRACE_RECENT_STATE_18";
export const QUESTIONNAIRE_VERSION = "1.2";
export const QUESTIONNAIRE_ITEM_SET_HASH = "mrs18-zh-cn-20261017-v2-balanced-keying";
export const SCORE_RULE_VERSION = "descriptive-rules/1.1-balanced-keying";

export const RESPONSE_OPTIONS = [
  { score: 0, label: "从未", days: "0 天" },
  { score: 1, label: "偶尔", days: "1～3 天" },
  { score: 2, label: "有时", days: "4～7 天" },
  { score: 3, label: "经常", days: "8～11 天" },
  { score: 4, label: "几乎每天", days: "12～14 天" },
] as const satisfies readonly { score: QuestionnaireScore; label: string; days: string }[];

const item = (number: number, domain: QuestionnaireDomain, domainLabel: string, text: string, scoringDirection: QuestionnaireItem["scoringDirection"] = "direct"): QuestionnaireItem => ({
  id: `MRS_${String(number).padStart(2, "0")}`,
  number,
  domain,
  domainLabel,
  text,
  scoringDirection,
});

export const QUESTIONNAIRE_ITEMS: readonly QuestionnaireItem[] = [
  item(1, "mood_interest", "心境与兴趣", "我感到心情低落、沮丧或情绪沉重。"),
  item(2, "mood_interest", "心境与兴趣", "我对平时愿意做的事情缺少兴趣。"),
  item(3, "mood_interest", "心境与兴趣", "我能从日常小事中感到愉快。", "reverse"),
  item(4, "mood_interest", "心境与兴趣", "我想到接下来的生活时，很难产生期待。"),
  item(5, "worry_tension", "担忧与紧张", "我反复想起担心的事情，很难让自己停下来。"),
  item(6, "worry_tension", "担忧与紧张", "事情尚未发生时，我就会担心出现不好的结果。"),
  item(7, "worry_tension", "担忧与紧张", "即使没有紧急事情，我也感到紧张或不安。"),
  item(8, "worry_tension", "担忧与紧张", "休息时，我能让身体和思绪放松下来。", "reverse"),
  item(9, "stress_coping", "压力与应对", "日常事情同时出现时，我感到难以应付。"),
  item(10, "stress_coping", "压力与应对", "原有计划被打乱后，我能逐步调整状态。", "reverse"),
  item(11, "stress_coping", "压力与应对", "遇到小麻烦时，我容易烦躁或发脾气。"),
  item(12, "stress_coping", "压力与应对", "面对需要处理的事情时，我常不知道从哪里开始。"),
  item(13, "sleep_energy_attention", "睡眠、精力与注意", "到了准备睡觉的时间，我仍迟迟无法入睡。"),
  item(14, "sleep_energy_attention", "睡眠、精力与注意", "夜间醒来或过早醒来后，我很难再次入睡。"),
  item(15, "sleep_energy_attention", "睡眠、精力与注意", "白天做日常事情时，我通常有足够的精力。", "reverse"),
  item(16, "sleep_energy_attention", "睡眠、精力与注意", "学习、工作或处理事情时，我很难持续集中注意力。"),
  item(17, "daily_function", "日常功能影响", "上述状态影响我完成学习、工作、家务或其他日常任务。"),
  item(18, "daily_function", "日常功能影响", "上述状态影响我与他人的正常交流或相处。"),
];

const symptomDomains = ["mood_interest", "worry_tension", "stress_coping", "sleep_energy_attention"] as const;

export function scoreQuestionnaireAnswer(item: QuestionnaireItem, answer: QuestionnaireAnswer): QuestionnaireAnswer {
  if (typeof answer !== "number") return answer;
  return item.scoringDirection === "reverse" ? (4 - answer) as QuestionnaireScore : answer;
}

export function calculateQuestionnaireSummary(
  answers: readonly QuestionnaireAnswer[],
  consentAccepted = true,
  responseTimesMs: readonly number[] = [],
) {
  const normalized = QUESTIONNAIRE_ITEMS.map((_, index) => answers[index]);
  const scored = QUESTIONNAIRE_ITEMS.map((entry, index) => scoreQuestionnaireAnswer(entry, normalized[index]));
  const valid = normalized.every((value) => value === undefined || value === null || Number.isInteger(value) && value >= 0 && value <= 4);
  const answeredCount = normalized.filter((value) => typeof value === "number").length;
  const resolvedCount = normalized.filter((value) => value !== undefined).length;
  const missingItemIds = QUESTIONNAIRE_ITEMS.filter((_, index) => normalized[index] === null).map((entry) => entry.id);
  const unansweredItemIds = QUESTIONNAIRE_ITEMS.filter((_, index) => normalized[index] === undefined).map((entry) => entry.id);
  const complete = answeredCount === QUESTIONNAIRE_ITEMS.length;

  const domainScores = Object.fromEntries([...symptomDomains, "daily_function"].map((domain) => {
    const domainValues = QUESTIONNAIRE_ITEMS.flatMap((entry, index) => entry.domain === domain ? [scored[index]] : []);
    const sum = domainValues.every((value) => typeof value === "number")
      ? domainValues.reduce<number>((total, value) => total + (value as number), 0)
      : null;
    return [domain, { answeredCount: domainValues.filter((value) => typeof value === "number").length, sum }];
  })) as Record<QuestionnaireDomain, { answeredCount: number; sum: number | null }>;

  const symptomValues = scored.slice(0, 16);
  const symptomsComplete = symptomValues.every((value) => typeof value === "number");
  const symptomSumS = symptomsComplete ? symptomValues.reduce<number>((total, value) => total + (value as number), 0) : null;
  const breadthB = symptomsComplete ? symptomValues.filter((value) => (value as number) >= 2).length : null;
  const frequentF = symptomsComplete ? symptomValues.filter((value) => (value as number) >= 3).length : null;
  const impactValues = scored.slice(16, 18);
  const impactI = impactValues.every((value) => typeof value === "number") ? Math.max(...impactValues as number[]) : null;

  let resultTitle: string | null = null;
  if (complete && impactI !== null && breadthB !== null && frequentF !== null) {
    if (impactI >= 3) resultTitle = "近期状态较频繁地影响了日常功能";
    else if (frequentF >= 3) resultTitle = "多项困扰较频繁出现";
    else if (frequentF >= 1) resultTitle = "有少量较频繁出现的困扰";
    else if (breadthB >= 5) resultTitle = "多项困扰间歇出现";
    else if (breadthB >= 1) resultTitle = "有一些间歇出现的困扰";
    else if (scored.some((value) => value === 1)) resultTitle = "本期报告了少量低频体验";
    else if (scored.every((value) => value === 0)) resultTitle = "本次未报告问卷列出的困扰";
  }

  const qcFlags: string[] = [];
  if (missingItemIds.length) qcFlags.push("missing_items");
  if (complete && normalized.every((value) => value === normalized[0])) qcFlags.push("all_same_response");
  if (symptomsComplete && symptomValues.every((value) => value === 0) && impactI !== null && impactI >= 3) qcFlags.push("impact_mismatch");
  const validResponseTimes = responseTimesMs.filter((value) => Number.isFinite(value) && value >= 0);
  const fastResponseCount = validResponseTimes.filter((value) => value < 1000).length;
  if (validResponseTimes.length === QUESTIONNAIRE_ITEMS.length && fastResponseCount >= 14) qcFlags.push("rapid_response_pattern");

  const recordStatus = !consentAccepted || !valid
    ? "excluded"
    : qcFlags.includes("impact_mismatch") || qcFlags.includes("rapid_response_pattern")
      ? "review_required"
      : complete
        ? "usable_full"
        : resolvedCount === QUESTIONNAIRE_ITEMS.length || answeredCount > 0
          ? "usable_partial"
          : "not_started";

  return {
    completionStatus: complete ? "complete" : resolvedCount === QUESTIONNAIRE_ITEMS.length ? "complete_with_missing" : "incomplete",
    answeredCount,
    missingItemIds,
    unansweredItemIds,
    domainScores,
    scoredItemValues: QUESTIONNAIRE_ITEMS.map((entry, index) => ({
      questionId: entry.id,
      scoringDirection: entry.scoringDirection,
      rawScore: typeof normalized[index] === "number" ? normalized[index] : null,
      scoredScore: typeof scored[index] === "number" ? scored[index] : null,
    })),
    symptomSumS,
    breadthB,
    frequentF,
    impactI,
    resultTitle,
    scoreRuleVersion: SCORE_RULE_VERSION,
    responseTiming: {
      recordedItemCount: validResponseTimes.length,
      totalMs: Math.round(validResponseTimes.reduce((total, value) => total + value, 0) * 10) / 10,
      underOneSecondCount: fastResponseCount,
      qualityRule: "review when at least 14 of 18 item responses are under 1000 ms",
    },
    quality: {
      recordStatus,
      qcFlags,
      exclusionReason: !consentAccepted ? "consent_not_granted" : !valid ? "invalid_response_value" : null,
      reviewedAt: null,
      reviewedBy: null,
    },
  };
}

export function formatLocalDate(date: Date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}
