import { expect, test } from "@playwright/test";
import {
  calculateStrokeTiming,
  STROKE_TIMING_DEFINITION,
  type StrokeTimingPoint,
} from "../src/strokeTiming";

const point = (elapsedMs: number, changes: Partial<StrokeTimingPoint> = {}): StrokeTimingPoint => ({
  strokeId: 1, pointerId: 1, phase: "move", x: 0, y: 0, elapsedMs, ...changes,
});
const stationaryStroke = (durationMs: number, intervalMs = 50) => Array.from(
  { length: durationMs / intervalMs + 1 },
  (_, index) => point(index * intervalMs, {
    phase: index === 0 ? "down" : index * intervalMs === durationMs ? "up" : "move",
  }),
);

test("empty and single-point attempts have no observed timing intervals", () => {
  const empty = {
    pauseInStrokeMs: 0, betweenStrokeMs: 0, pauseInStrokeCount: 0,
    betweenStrokeCount: 0, unobservedIntervalMs: 0,
  };
  expect(calculateStrokeTiming([])).toEqual(empty);
  expect(calculateStrokeTiming([point(900, { phase: "down" })])).toEqual(empty);
});

test("explicit pen-up intervals are separate from within-stroke pauses, including short gaps", () => {
  const result = calculateStrokeTiming([
    point(0, { phase: "down" }), point(100, { phase: "up", x: 20 }),
    point(600, { strokeId: 2, phase: "down" }), point(700, { strokeId: 2, phase: "up", x: 20 }),
    point(780, { strokeId: 3, phase: "down" }), point(880, { strokeId: 3, phase: "up", x: 20 }),
  ]);
  expect(result).toEqual({
    pauseInStrokeMs: 0, betweenStrokeMs: 580, pauseInStrokeCount: 0,
    betweenStrokeCount: 2, unobservedIntervalMs: 0,
  });
});

test("a full observed low-speed run qualifies at 500 ms but not at 450 ms", () => {
  expect(calculateStrokeTiming(stationaryStroke(500))).toMatchObject({
    pauseInStrokeMs: 500, pauseInStrokeCount: 1, betweenStrokeMs: 0, unobservedIntervalMs: 0,
  });
  expect(calculateStrokeTiming(stationaryStroke(450))).toMatchObject({
    pauseInStrokeMs: 0, pauseInStrokeCount: 0, unobservedIntervalMs: 0,
  });
});

test("100 ms sampling and 5 CSS px/s speed thresholds are inclusive", () => {
  const atThreshold = stationaryStroke(500, 100).map((sample, index) => ({ ...sample, x: index * 0.5 }));
  expect(calculateStrokeTiming(atThreshold).pauseInStrokeMs).toBe(500);
  const moving = atThreshold.map((sample, index) => ({ ...sample, x: index * 0.51 }));
  expect(calculateStrokeTiming(moving)).toMatchObject({ pauseInStrokeMs: 0, unobservedIntervalMs: 0 });
});

test("a long sampling gap never establishes a pause from matching or moving endpoints", () => {
  for (const x of [0, 100]) {
    const result = calculateStrokeTiming([
      point(0, { phase: "down" }), point(1000, { phase: "up", x }),
    ]);
    expect(result).toMatchObject({
      pauseInStrokeMs: 0, pauseInStrokeCount: 0, betweenStrokeMs: 0, unobservedIntervalMs: 1000,
    });
  }
});

test("a sampling gap above 100 ms splits two otherwise stationary runs", () => {
  const before = stationaryStroke(300).map(sample => ({ ...sample, phase: sample.phase === "up" ? "move" as const : sample.phase }));
  const after = stationaryStroke(300).map(sample => ({
    ...sample, elapsedMs: sample.elapsedMs + 401, phase: sample.phase === "down" ? "move" as const : sample.phase,
  }));
  expect(calculateStrokeTiming([...before, ...after])).toMatchObject({
    pauseInStrokeMs: 0, pauseInStrokeCount: 0, unobservedIntervalMs: 101,
  });
});

test("movement separates qualified pauses instead of joining them", () => {
  const before = stationaryStroke(500).map(sample => ({ ...sample, phase: sample.phase === "up" ? "move" as const : sample.phase }));
  const after = stationaryStroke(500).map(sample => ({
    ...sample, elapsedMs: sample.elapsedMs + 550, x: 10,
    phase: sample.phase === "down" ? "move" as const : sample.phase,
  }));
  expect(calculateStrokeTiming([...before, ...after])).toMatchObject({
    pauseInStrokeMs: 1000, pauseInStrokeCount: 2, unobservedIntervalMs: 0,
  });
});

test("a changed pointer cannot continue a pause even if stroke IDs match", () => {
  const first = stationaryStroke(300).map(sample => ({ ...sample, phase: sample.phase === "up" ? "move" as const : sample.phase }));
  const second = stationaryStroke(300).map(sample => ({ ...sample, pointerId: 2, elapsedMs: sample.elapsedMs + 350 }));
  expect(calculateStrokeTiming([...first, ...second])).toMatchObject({
    pauseInStrokeMs: 0, betweenStrokeMs: 0, betweenStrokeCount: 0, unobservedIntervalMs: 50,
  });
  expect(calculateStrokeTiming([
    point(100, { phase: "up" }), point(600, { phase: "down", pointerId: 2 }),
  ])).toMatchObject({ betweenStrokeMs: 500, betweenStrokeCount: 1, unobservedIntervalMs: 0 });
});

test("cancelled strokes without an up boundary leave the next interval unobserved", () => {
  expect(calculateStrokeTiming([
    point(0, { phase: "down" }), point(100, { x: 20 }),
    point(1100, { strokeId: 2, phase: "down" }),
    point(1200, { strokeId: 2, phase: "up", x: 20 }),
  ])).toEqual({
    pauseInStrokeMs: 0, betweenStrokeMs: 0, pauseInStrokeCount: 0,
    betweenStrokeCount: 0, unobservedIntervalMs: 1000,
  });
});

test("a down inside the same stroke cannot supply a pen-up boundary", () => {
  expect(calculateStrokeTiming([
    point(100, { phase: "up" }), point(600, { phase: "down" }),
  ])).toMatchObject({ betweenStrokeMs: 0, betweenStrokeCount: 0, unobservedIntervalMs: 500 });
});

test("zero, reversed and invalid timestamps break low-speed runs without adding time", () => {
  for (const invalidTime of [250, 200, Number.NaN, Number.POSITIVE_INFINITY]) {
    const first = stationaryStroke(250).map(sample => ({ ...sample, phase: sample.phase === "up" ? "move" as const : sample.phase }));
    const second = stationaryStroke(250).map(sample => ({
      ...sample, elapsedMs: sample.elapsedMs + 300, phase: sample.phase === "down" ? "move" as const : sample.phase,
    }));
    const result = calculateStrokeTiming([...first, point(invalidTime), ...second]);
    expect(result.pauseInStrokeMs).toBe(0);
    expect(result.pauseInStrokeCount).toBe(0);
    expect(Number.isFinite(result.unobservedIntervalMs)).toBe(true);
  }
  expect(calculateStrokeTiming([
    point(100, { phase: "up" }), point(100, { phase: "down", strokeId: 2 }),
  ])).toMatchObject({ betweenStrokeMs: 0, betweenStrokeCount: 1, unobservedIntervalMs: 0 });
});

test("invalid coordinates leave within-stroke intervals unobserved", () => {
  expect(calculateStrokeTiming([
    point(0, { phase: "down" }), point(100, { x: Number.NaN }), point(200, { phase: "up" }),
  ])).toMatchObject({ pauseInStrokeMs: 0, betweenStrokeMs: 0, unobservedIntervalMs: 200 });
});

test("retained and restored strokes keep timing independent of the elapsed origin", () => {
  const retained = stationaryStroke(500);
  const original = retained.map(sample => Object.freeze({ ...sample }));
  const shifted = retained.map(sample => ({ ...sample, elapsedMs: sample.elapsedMs + 900 }));
  expect(calculateStrokeTiming(shifted)).toEqual(calculateStrokeTiming(original));
  expect(calculateStrokeTiming([]).pauseInStrokeMs).toBe(0);
  expect(calculateStrokeTiming([...original]).pauseInStrokeMs).toBe(500);
  expect(original[0].elapsedMs).toBe(0);
  expect(original.at(-1)?.elapsedMs).toBe(500);
});

test("exported method metadata makes units, thresholds and missing-sample limits explicit", () => {
  expect(STROKE_TIMING_DEFINITION).toMatchObject({
    version: "1.0.0", timeUnit: "ms", distanceUnit: "CSS_px", minPauseDurationMs: 500,
    maxPauseSpeedPxPerSecond: 5, maxObservedGapMs: 100, betweenStroke: "explicit_up_to_next_down",
  });
  expect(STROKE_TIMING_DEFINITION.limitation).toContain("Missing samples do not establish a pause");
});
