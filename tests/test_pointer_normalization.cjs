"use strict";

const assert = require("node:assert/strict");
const pointer = require("../frontend/src/features/handwriting/pointer-normalization.cjs");

assert.equal(pointer.pointerType({ pointerType: "" }, { pointerType: "pen" }), "pen");
assert.equal(pointer.pressure({ pressure: 0.73 }, { pointerType: "pen" }), 0.73);
assert.equal(pointer.pressure({ pressure: 0.5 }, { pointerType: "mouse" }), null);

const inherited = pointer.tilt(
  { pointerType: "", tiltX: 0, tiltY: 0 },
  { pointerType: "pen", tiltX: 18, tiltY: -12 }
);
assert.deepEqual({ x: inherited.x, y: inherited.y }, { x: 18, y: -12 });

const derived = pointer.tilt(
  { tiltX: 0, tiltY: 0, altitudeAngle: Math.PI / 4, azimuthAngle: 0 },
  { pointerType: "pen" }
);
assert.ok(Math.abs(derived.x - 45) < 0.001);
console.log("pointer normalization tests passed");
