"use strict";

const assert = require("node:assert/strict");
const pointer = require("../local/ai-lab/handwriting/collector/pointer-normalization.js");

assert.equal(
  pointer.pointerType({ pointerType: "" }, { pointerType: "pen" }),
  "pen",
  "coalesced samples must inherit the parent pointer type"
);
assert.equal(
  pointer.pressure({ pressure: 0.73 }, { pointerType: "pen" }),
  0.73,
  "pressure must remain available when the coalesced sample omits pointerType"
);
assert.equal(pointer.pressure({ pressure: 0.5 }, { pointerType: "mouse" }), null);

const parentTilt = pointer.tilt(
  { pointerType: "", tiltX: 0, tiltY: 0 },
  { pointerType: "pen", tiltX: 18, tiltY: -12 }
);
assert.deepEqual({ x: parentTilt.x, y: parentTilt.y }, { x: 18, y: -12 }, "incomplete samples inherit parent tilt");

const angleTilt = pointer.tilt(
  { tiltX: 0, tiltY: 0, altitudeAngle: Math.PI / 4, azimuthAngle: 0 },
  { pointerType: "pen" }
);
assert.ok(Math.abs(angleTilt.x - 45) < 0.001);
assert.ok(Math.abs(angleTilt.y) < 0.001);

const verticalTilt = pointer.tilt(
  { tiltX: 0, tiltY: 0, altitudeAngle: Math.PI / 2, azimuthAngle: 1 },
  { pointerType: "pen" }
);
assert.ok(Math.abs(verticalTilt.x) < 0.001);
assert.ok(Math.abs(verticalTilt.y) < 0.001);

console.log("pointer normalization tests passed");
