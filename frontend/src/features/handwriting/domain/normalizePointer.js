function finite(value) {
  return Number.isFinite(value) ? Number(value) : null
}

function firstFinite(primary, fallback) {
  return finite(primary) ?? finite(fallback)
}

export function pointerType(sample, parentEvent) {
  return sample?.pointerType || parentEvent?.pointerType || 'unknown'
}

export function pressure(sample, parentEvent) {
  if (pointerType(sample, parentEvent) !== 'pen') return null
  return firstFinite(sample?.pressure, parentEvent?.pressure)
}

function clampTilt(value) {
  return Math.max(-90, Math.min(90, value))
}

function tiltFromAngles(altitude, azimuth) {
  const radiansToDegrees = 180 / Math.PI
  return {
    x: clampTilt(Math.atan2(Math.cos(azimuth), Math.tan(altitude)) * radiansToDegrees),
    y: clampTilt(Math.atan2(Math.sin(azimuth), Math.tan(altitude)) * radiansToDegrees),
  }
}

export function tilt(sample, parentEvent) {
  const incompleteSample = !sample?.pointerType && Boolean(parentEvent?.pointerType)
  const sampleX = finite(sample?.tiltX)
  const sampleY = finite(sample?.tiltY)
  const parentX = finite(parentEvent?.tiltX)
  const parentY = finite(parentEvent?.tiltY)
  const directX = incompleteSample && sampleX === 0 ? (parentX ?? sampleX) : (sampleX ?? parentX)
  const directY = incompleteSample && sampleY === 0 ? (parentY ?? sampleY) : (sampleY ?? parentY)
  const altitude = firstFinite(sample?.altitudeAngle, parentEvent?.altitudeAngle)
  const azimuth = firstFinite(sample?.azimuthAngle, parentEvent?.azimuthAngle)

  if (altitude !== null && azimuth !== null && altitude >= 0 && altitude <= Math.PI / 2) {
    const derived = tiltFromAngles(altitude, azimuth)
    if (
      directX === null ||
      directY === null ||
      (directX === 0 && directY === 0 && (derived.x !== 0 || derived.y !== 0))
    ) {
      return { x: derived.x, y: derived.y }
    }
  }
  return { x: directX, y: directY }
}

export function normalizePointer(sample, parentEvent, canvas, session) {
  const rect = canvas.getBoundingClientRect()
  const x = Math.max(0, Math.min(rect.width, sample.clientX - rect.left))
  const y = Math.max(0, Math.min(rect.height, sample.clientY - rect.top))
  const angles = tilt(sample, parentEvent)

  return {
    strokeId: session.strokeId,
    sequence: session.nextSequence(),
    phase: session.phase,
    pointerType: pointerType(sample, parentEvent),
    timestampEpochMs: Date.now(),
    elapsedMs: Math.max(0, Math.round(performance.now() - session.startedAt)),
    x: Number(x.toFixed(3)),
    y: Number(y.toFixed(3)),
    xNorm: rect.width ? Number((x / rect.width).toFixed(6)) : 0,
    yNorm: rect.height ? Number((y / rect.height).toFixed(6)) : 0,
    canvasWidth: Number(rect.width.toFixed(3)),
    canvasHeight: Number(rect.height.toFixed(3)),
    pressure: pressure(sample, parentEvent),
    tiltX: angles.x,
    tiltY: angles.y,
    twist: firstFinite(sample?.twist, parentEvent?.twist),
    tangentialPressure: firstFinite(sample?.tangentialPressure, parentEvent?.tangentialPressure),
    contactWidth: firstFinite(sample?.width, parentEvent?.width),
    contactHeight: firstFinite(sample?.height, parentEvent?.height),
  }
}
