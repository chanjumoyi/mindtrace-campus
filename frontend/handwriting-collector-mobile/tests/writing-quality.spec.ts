import { expect, test } from "@playwright/test";
import { assessWritingPattern } from "../src/writingQuality";

test("the supplied scribble-like repeated copies are rejected by combined signals", () => {
  const first = assessWritingPattern("copy_sentence", {
    strokeCount: 25, durationMs: 7829.7, meanStrokePathLengthPx: 260.7,
    meanStrokeStraightness: 0.663, meanHorizontalDisplacementRatio: 0.456,
    meanAbsoluteTurnRadiansPer100Px: 6.87,
  }, 20);
  const second = assessWritingPattern("copy_sentence", {
    strokeCount: 26, durationMs: 6740.8, meanStrokePathLengthPx: 207.3,
    meanStrokeStraightness: 0.675, meanHorizontalDisplacementRatio: 0.381,
    meanAbsoluteTurnRadiansPer100Px: 8.38,
  }, 20);
  expect(first.blocking).toBe(true);
  expect(second.blocking).toBe(true);
  expect(first.qcFlags).toContain("suspected_non_text_scribble");
});

test("a prior character-like copy sample remains accepted", () => {
  const result = assessWritingPattern("copy_sentence", {
    strokeCount: 61, durationMs: 24423.7, meanStrokePathLengthPx: 56.9,
    meanStrokeStraightness: 0.598, meanHorizontalDisplacementRatio: 0.387,
    meanAbsoluteTurnRadiansPer100Px: 55.84,
  }, 19);
  expect(result.blocking).toBe(false);
  expect(result.qcFlags).toEqual([]);
});

test("the supplied scribble-like free writing is rejected without relying on one threshold", () => {
  const result = assessWritingPattern("free_writing", {
    strokeCount: 16, durationMs: 5556.5, meanStrokePathLengthPx: 106.1,
    meanStrokeStraightness: 0.502, meanHorizontalDisplacementRatio: 0.225,
    meanAbsoluteTurnRadiansPer100Px: 25.19,
  });
  expect(result.blocking).toBe(true);
  expect(result.suspiciousSignalCount).toBeGreaterThanOrEqual(2);
});
