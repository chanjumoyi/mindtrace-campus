export type WritingPatternKind = "pressure_check" | "copy_sentence" | "free_writing";

export type WritingPatternMetrics = {
  strokeCount: number;
  durationMs: number;
  meanStrokePathLengthPx: number;
  meanStrokeStraightness: number;
  meanHorizontalDisplacementRatio: number;
  meanAbsoluteTurnRadiansPer100Px: number;
};

export type WritingPatternAssessment = {
  qcFlags: string[];
  blocking: boolean;
  suspiciousSignalCount: number;
};

export function assessWritingPattern(
  kind: WritingPatternKind,
  metrics: WritingPatternMetrics,
  expectedCharacterCount: number | null = null,
): WritingPatternAssessment {
  const qcFlags: string[] = [];
  if (kind === "pressure_check") {
    if (metrics.meanStrokeStraightness < 0.75 || metrics.meanHorizontalDisplacementRatio < 0.7) {
      qcFlags.push("pressure_check_not_horizontal");
    }
    return { qcFlags, blocking: qcFlags.length > 0, suspiciousSignalCount: qcFlags.length };
  }

  const signals: string[] = [];
  if (kind === "copy_sentence") {
    const conservativeMinimumStrokes = Math.max(30, Math.ceil((expectedCharacterCount ?? 19) * 1.7));
    if (metrics.strokeCount < conservativeMinimumStrokes) signals.push("too_few_strokes_for_copy_prompt");
    if (metrics.durationMs < 9000) signals.push("copy_duration_implausibly_short");
    if (metrics.meanStrokePathLengthPx > 140) signals.push("overlong_continuous_strokes");
    if (metrics.meanAbsoluteTurnRadiansPer100Px < 10) signals.push("low_character_like_turning");
  } else {
    if (metrics.strokeCount < 20) signals.push("too_few_strokes_for_free_writing");
    if (metrics.durationMs < 6000) signals.push("free_writing_duration_implausibly_short");
    if (metrics.meanStrokePathLengthPx > 95) signals.push("overlong_continuous_strokes");
    if (metrics.meanAbsoluteTurnRadiansPer100Px < 30) signals.push("low_character_like_turning");
  }

  if (signals.length >= 2) qcFlags.push("suspected_non_text_scribble", ...signals);
  return { qcFlags, blocking: signals.length >= 2, suspiciousSignalCount: signals.length };
}
