import { expect, test } from "@playwright/test";
import { QUESTIONNAIRE_ITEMS, calculateQuestionnaireSummary } from "../src/questionnaire";

test("the questionnaire exposes the fixed 18-item data contract", () => {
  expect(QUESTIONNAIRE_ITEMS).toHaveLength(18);
  expect(new Set(QUESTIONNAIRE_ITEMS.map((item) => item.id)).size).toBe(18);
  expect(QUESTIONNAIRE_ITEMS[0].id).toBe("MRS_01");
  expect(QUESTIONNAIRE_ITEMS[17].domain).toBe("daily_function");
});

test("zero is a valid answer and produces the all-zero descriptive result", () => {
  const summary = calculateQuestionnaireSummary(Array(18).fill(0));
  expect(summary.completionStatus).toBe("complete");
  expect(summary.answeredCount).toBe(18);
  expect(summary.symptomSumS).toBe(0);
  expect(summary.breadthB).toBe(0);
  expect(summary.frequentF).toBe(0);
  expect(summary.impactI).toBe(0);
  expect(summary.resultTitle).toBe("本次未报告问卷列出的困扰");
  expect(summary.quality.recordStatus).toBe("usable_full");
  expect(summary.quality.qcFlags).toContain("all_same_response");
});

test("missing answers stay null and suppress complete derived scores", () => {
  const answers = Array(18).fill(1);
  answers[4] = null;
  const summary = calculateQuestionnaireSummary(answers);
  expect(summary.completionStatus).toBe("complete_with_missing");
  expect(summary.missingItemIds).toEqual(["MRS_05"]);
  expect(summary.symptomSumS).toBeNull();
  expect(summary.breadthB).toBeNull();
  expect(summary.frequentF).toBeNull();
  expect(summary.domainScores.worry_tension.sum).toBeNull();
  expect(summary.quality.recordStatus).toBe("usable_partial");
});

test("derived domain, breadth, frequency and impact rules are stable", () => {
  const answers = [3, 3, 3, 0, 2, 2, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 2, 1];
  const summary = calculateQuestionnaireSummary(answers);
  expect(summary.domainScores.mood_interest.sum).toBe(9);
  expect(summary.domainScores.worry_tension.sum).toBe(4);
  expect(summary.symptomSumS).toBe(17);
  expect(summary.breadthB).toBe(5);
  expect(summary.frequentF).toBe(3);
  expect(summary.impactI).toBe(2);
  expect(summary.resultTitle).toBe("多项困扰较频繁出现");
});

test("an impact-only response is retained but flagged for review", () => {
  const answers = [...Array(16).fill(0), 3, 0];
  const summary = calculateQuestionnaireSummary(answers);
  expect(summary.quality.recordStatus).toBe("review_required");
  expect(summary.quality.qcFlags).toContain("impact_mismatch");
});

test("a single low-frequency impact response receives the low-frequency title", () => {
  const answers = [...Array(16).fill(0), 1, 0];
  const summary = calculateQuestionnaireSummary(answers);
  expect(summary.resultTitle).toBe("本期报告了少量低频体验");
  expect(summary.quality.recordStatus).toBe("usable_full");
});

test("missing consent excludes the record without changing answers", () => {
  const summary = calculateQuestionnaireSummary(Array(18).fill(1), false);
  expect(summary.answeredCount).toBe(18);
  expect(summary.quality.recordStatus).toBe("excluded");
  expect(summary.quality.exclusionReason).toBe("consent_not_granted");
});
