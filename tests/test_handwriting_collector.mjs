import assert from "node:assert/strict";

Object.defineProperty(globalThis, "navigator", {
  configurable: true,
  value: {
    userAgent: "MindLine test browser",
    platform: "test",
    maxTouchPoints: 1,
  },
});
Object.defineProperty(globalThis, "window", {
  configurable: true,
  value: { devicePixelRatio: 2 },
});

const { buildCollectionPackage, buildTrace } = await import(
  "../frontend/src/features/handwriting/domain/buildTrace.js"
);

const task = {
  code: "COPY",
  type: "copy_text",
  prompt: "今天的风很轻。",
};
const questionnaire = {
  stressLevel: 3,
  moodLevel: 4,
  fatigueLevel: 2,
  sleepQuality: 4,
};
const points = [
  {
    strokeId: 1,
    sequence: 1,
    phase: "down",
    pointerType: "pen",
    timestampEpochMs: 1000,
    elapsedMs: 0,
    pressure: 0.2,
    tiltX: 10,
    tiltY: 5,
  },
  {
    strokeId: 1,
    sequence: 2,
    phase: "up",
    pointerType: "pen",
    timestampEpochMs: 1100,
    elapsedMs: 100,
    pressure: 0.6,
    tiltX: 11,
    tiltY: 5,
  },
];

const trace = buildTrace({
  participantId: "P-TEST",
  task,
  questionnaire,
  snapshot: {
    points,
    strokeCount: 1,
    canvas: { width: 320, height: 480, background: "#fffdf7" },
  },
});

assert.equal(trace.schemaVersion, "1.0.0");
assert.equal(trace.summary.pointCount, 2);
assert.equal(trace.summary.strokeCount, 1);
assert.equal(trace.device.supportsPressure, true);
assert.equal(trace.selfReport.stressLevel, 3);
assert.match(trace.selfReport.note, /fatigue:2/);

const collection = buildCollectionPackage({
  participantId: "P-TEST",
  roundId: "R-001",
  questionnaire,
  attempts: [trace],
});

assert.equal(collection.participantId, "P-TEST");
assert.equal(collection.roundId, "R-001");
assert.equal(collection.attempts.length, 1);
console.log("handwriting collector tests passed");
