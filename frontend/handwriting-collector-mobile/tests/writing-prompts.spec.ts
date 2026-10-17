import { expect, test } from "@playwright/test";
import { COPY_PROMPT_POOL, selectCopyPrompt } from "../src/writingPrompts";

test("the universal positive pool contains length-matched prompts", () => {
  expect(COPY_PROMPT_POOL).toHaveLength(9);
  expect(Math.max(...COPY_PROMPT_POOL.map((entry) => entry.characterCount)) - Math.min(...COPY_PROMPT_POOL.map((entry) => entry.characterCount))).toBeLessThanOrEqual(1);
  expect(COPY_PROMPT_POOL.every((entry) => entry.characterCount >= 19 && entry.characterCount <= 20)).toBe(true);
});

test("prompt selection is independent of questionnaire score and records assignment metadata", () => {
  const assignment = selectCopyPrompt(2);
  expect(assignment.id).toBe("CP_P_03");
  expect(assignment.poolId).toBe("universal_positive");
  expect(assignment).not.toHaveProperty("questionnaireSymptomSum");
  expect(assignment).not.toHaveProperty("bandId");
  expect(assignment.selectionMethod).toBe("injected_index");
});
