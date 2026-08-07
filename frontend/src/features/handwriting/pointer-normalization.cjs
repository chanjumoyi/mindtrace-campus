;(function (root, factory) {
  'use strict'

  const api = factory()
  if (typeof module === 'object' && module.exports) module.exports = api
  if (root) root.MindLinePointer = api
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict'

  function finite(value) {
    return Number.isFinite(value) ? Number(value) : null
  }

  function firstFinite(primary, fallback) {
    return finite(primary) ?? finite(fallback)
  }

  function pointerType(sample, parentEvent) {
    return sample?.pointerType || parentEvent?.pointerType || 'unknown'
  }

  function pressure(sample, parentEvent) {
    if (pointerType(sample, parentEvent) !== 'pen') return null
    return firstFinite(sample?.pressure, parentEvent?.pressure)
  }

  function tilt(sample, parentEvent) {
    const incompleteSample = !sample?.pointerType && Boolean(parentEvent?.pointerType)
    const sampleX = finite(sample?.tiltX)
    const sampleY = finite(sample?.tiltY)
    const parentX = finite(parentEvent?.tiltX)
    const parentY = finite(parentEvent?.tiltY)
    const directX =
      incompleteSample && sampleX === 0 && parentX !== null ? parentX : (sampleX ?? parentX)
    const directY =
      incompleteSample && sampleY === 0 && parentY !== null ? parentY : (sampleY ?? parentY)
    // Angle fields can still carry real values on an otherwise incomplete sample.
    const altitude = firstFinite(sample?.altitudeAngle, parentEvent?.altitudeAngle)
    const azimuth = firstFinite(sample?.azimuthAngle, parentEvent?.azimuthAngle)

    // Some Windows pen stacks expose the newer angle pair but leave tiltX/tiltY
    // at their default zero values. Prefer the angle-derived value in that case.
    if (altitude !== null && azimuth !== null && altitude >= 0 && altitude <= Math.PI / 2) {
      const derived = tiltFromAngles(altitude, azimuth)
      if (
        directX === null ||
        directY === null ||
        (directX === 0 && directY === 0 && (derived.x !== 0 || derived.y !== 0))
      ) {
        return { x: derived.x, y: derived.y, altitude, azimuth }
      }
    }

    return { x: directX, y: directY, altitude, azimuth }
  }

  function tiltFromAngles(altitude, azimuth) {
    const radiansToDegrees = 180 / Math.PI
    const x = Math.atan2(Math.cos(azimuth), Math.tan(altitude)) * radiansToDegrees
    const y = Math.atan2(Math.sin(azimuth), Math.tan(altitude)) * radiansToDegrees
    return { x: clampTilt(x), y: clampTilt(y) }
  }

  function clampTilt(value) {
    return Math.max(-90, Math.min(90, value))
  }

  return { finite, pointerType, pressure, tilt, tiltFromAngles }
})
