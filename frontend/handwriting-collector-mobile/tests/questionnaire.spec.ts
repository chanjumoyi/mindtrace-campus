import { expect, test } from "@playwright/test";
import { QUESTIONNAIRE_ITEMS, RESPONSE_OPTIONS, calculateQuestionnaireSummary as score, type QuestionnaireAnswer } from "../src/questionnaire";
test("official five items, six options, positive direction", () => {
  expect(QUESTIONNAIRE_ITEMS).toHaveLength(5);
  expect(new Set(QUESTIONNAIRE_ITEMS.map(i => i.id)).size).toBe(5);
  expect(RESPONSE_OPTIONS.map(i => i.score)).toEqual([5,4,3,2,1,0]);
  expect(QUESTIONNAIRE_ITEMS.every(i => i.scoringDirection === "direct")).toBe(true);
});
test("official cutoff boundary and percentage transformation", () => {
  expect(score([2,2,2,3,3])).toMatchObject({rawTotal:12,percentageScore:48,belowCutoff:true,needsFurtherAssessment:true});
  expect(score([2,2,3,3,3])).toMatchObject({rawTotal:13,percentageScore:52,belowCutoff:false,needsFurtherAssessment:false});
});
test("Chinese low-item rule remains distinct from total threshold", () => {
  expect(score([1,5,5,5,5])).toMatchObject({rawTotal:21,belowCutoff:false,lowItemIds:["WHO5_01"],needsFurtherAssessment:true});
});
test("uniform answers remain valid and endpoints are correct", () => {
  for (const value of [0,5] as const) {
    expect(score(Array(5).fill(value))).toMatchObject({rawTotal:value*5,percentageScore:value*20,quality:{recordStatus:"usable_full"}});
  }
});
test("missing or invalid data cannot produce any assessment", () => {
  for (const answers of [[5,null,5,5,5],[5],[5,5,5,5,6],[NaN,5,5,5,5],[2.5,5,5,5,5],Array(6).fill(5)]) {
    expect(score(answers as QuestionnaireAnswer[])).toMatchObject({rawTotal:null,percentageScore:null,needsFurtherAssessment:null,resultTitle:null});
  }
  expect(score([5,5,5,5,5],false)).toMatchObject({rawTotal:null,quality:{recordStatus:"excluded"}});
  expect(score([5,null,5,5,5]).missingItemIds).toEqual(["WHO5_02"]);
  expect(score([5]).unansweredItemIds).toHaveLength(4);
});
test("timing review never changes the assessment", () => {
  expect(score([5,5,5,5,5],true,[700,700,700,700,1200])).toMatchObject({rawTotal:25,needsFurtherAssessment:false,quality:{recordStatus:"review_required"}});
});
