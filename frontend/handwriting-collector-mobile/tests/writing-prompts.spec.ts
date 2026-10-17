import { expect, test } from "@playwright/test";
import { COPY_PROMPT_POOLS, getCopyPromptBand, selectCopyPrompt } from "../src/writingPrompts";

test("each scored writing band contains three length-matched prompts", () => {
  for (const bandId of ["range_0_15", "range_16_31", "range_32_47", "range_48_64"] as const) {
    const pool = COPY_PROMPT_POOLS[bandId];
    expect(pool).toHaveLength(3);
    expect(Math.max(...pool.map((entry) => entry.characterCount)) - Math.min(...pool.map((entry) => entry.characterCount))).toBeLessThanOrEqual(1);
    expect(pool.every((entry) => entry.characterCount >= 19 && entry.characterCount <= 20)).toBe(true);
  }
});

test("score boundaries select the documented writing bands", () => {
  expect(getCopyPromptBand(0).bandId).toBe("range_0_15");
  expect(getCopyPromptBand(15).bandId).toBe("range_0_15");
  expect(getCopyPromptBand(16).bandId).toBe("range_16_31");
  expect(getCopyPromptBand(31).bandId).toBe("range_16_31");
  expect(getCopyPromptBand(32).bandId).toBe("range_32_47");
  expect(getCopyPromptBand(47).bandId).toBe("range_32_47");
  expect(getCopyPromptBand(48).bandId).toBe("range_48_64");
  expect(getCopyPromptBand(64).bandId).toBe("range_48_64");
  expect(getCopyPromptBand(null).bandId).toBe("unscored");
});

test("prompt selection stays inside the score band and records assignment metadata", () => {
  const assignment = selectCopyPrompt(22, 2);
  expect(assignment.bandId).toBe("range_16_31");
  expect(assignment.id).toBe("CP_B_03");
  expect(assignment.questionnaireSymptomSum).toBe(22);
  expect(assignment.selectionMethod).toBe("injected_index");
});
