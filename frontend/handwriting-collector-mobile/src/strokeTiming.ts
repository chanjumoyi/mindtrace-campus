/** Only the raw fields needed for the timing calculation; acquisition points may contain more. */
export type StrokeTimingPoint = {
  strokeId: number;
  pointerId: number;
  phase: "down" | "move" | "up";
  x: number;
  y: number;
  elapsedMs: number;
};

export const STROKE_TIMING_DEFINITION = {
  version: "1.0.0",
  timeUnit: "ms",
  distanceUnit: "CSS_px",
  minPauseDurationMs: 500,
  maxPauseSpeedPxPerSecond: 5,
  maxObservedGapMs: 100,
  pauseInStroke: "contiguous_observed_low_speed_intervals",
  betweenStroke: "explicit_up_to_next_down",
  betweenStrokeCount: "nonnegative_explicit_up_to_next_down_intervals",
  unobservedInterval: "positive_adjacent_intervals_without_observed_stroke_or_explicit_pen_up_boundary",
  limitation: "Observed low-speed estimates are not direct observations of thinking. Missing samples do not establish a pause.",
} as const;

export type StrokeTiming = {
  pauseInStrokeMs: number;
  betweenStrokeMs: number;
  pauseInStrokeCount: number;
  betweenStrokeCount: number;
  unobservedIntervalMs: number;
};

/**
 * Measures retained ink in acquisition order, without rebasing or modifying raw timestamps.
 *
 * A pause requires a continuous run of low-speed, closely sampled intervals. A single long
 * gap cannot distinguish a stationary pen from missing movement samples, even if its endpoint
 * coordinates match. Known pen-up boundaries are measured separately, without a minimum gap.
 *
 * Each positive adjacent interval is either an explicit pen-up interval, an observed within-
 * stroke interval, or unobserved. Moving and short low-speed observed intervals are neither
 * pauses nor unobserved. Missing up/down boundaries and invalid coordinates remain unobserved;
 * duplicate, reversed, or invalid timestamps break a pause run and add no duration.
 */
export function calculateStrokeTiming(points: readonly StrokeTimingPoint[]): StrokeTiming {
  const result: StrokeTiming = {
    pauseInStrokeMs: 0,
    betweenStrokeMs: 0,
    pauseInStrokeCount: 0,
    betweenStrokeCount: 0,
    unobservedIntervalMs: 0,
  };
  let lowSpeedDurationMs = 0;
  const finishPause = () => {
    if (lowSpeedDurationMs >= STROKE_TIMING_DEFINITION.minPauseDurationMs) {
      result.pauseInStrokeMs += lowSpeedDurationMs;
      result.pauseInStrokeCount += 1;
    }
    lowSpeedDurationMs = 0;
  };

  for (let index = 1; index < points.length; index += 1) {
    const previous = points[index - 1];
    const current = points[index];
    const deltaMs = current.elapsedMs - previous.elapsedMs;
    if (!Number.isFinite(deltaMs) || deltaMs < 0) {
      finishPause();
      continue;
    }

    const sameStrokeAndPointer = current.strokeId === previous.strokeId
      && current.pointerId === previous.pointerId;
    if (previous.phase === "up" && current.phase === "down" && !sameStrokeAndPointer) {
      finishPause();
      result.betweenStrokeMs += deltaMs;
      result.betweenStrokeCount += 1;
      continue;
    }

    if (deltaMs === 0) {
      finishPause();
      continue;
    }
    const observedWithinStroke = sameStrokeAndPointer
      && previous.phase !== "up" && current.phase !== "down"
      && deltaMs <= STROKE_TIMING_DEFINITION.maxObservedGapMs
      && Number.isFinite(previous.x) && Number.isFinite(previous.y)
      && Number.isFinite(current.x) && Number.isFinite(current.y);
    if (!observedWithinStroke) {
      finishPause();
      result.unobservedIntervalMs += deltaMs;
      continue;
    }

    const speed = Math.hypot(current.x - previous.x, current.y - previous.y) / deltaMs * 1000;
    if (speed <= STROKE_TIMING_DEFINITION.maxPauseSpeedPxPerSecond) {
      lowSpeedDurationMs += deltaMs;
    } else {
      finishPause();
    }
  }
  finishPause();
  return result;
}
