import { NOTICE_VERSION } from '../constants.js'

function isoFromEpoch(value) {
  return value == null ? null : new Date(value).toISOString()
}

function pressureIsAvailable(points) {
  const values = points
    .map((point) => point.pressure)
    .filter((value) => Number.isFinite(value) && value > 0)
  return values.length > 1 && Math.max(...values) - Math.min(...values) >= 0.01
}

export function buildTrace({ participantId, task, questionnaire, snapshot }) {
  const points = snapshot.points
  const firstPoint = points[0]
  const lastPoint = points.at(-1)
  const pointerTypes = [...new Set(points.map((point) => point.pointerType))]

  return {
    schemaVersion: '1.0.0',
    sessionId: crypto.randomUUID(),
    participantId,
    task: {
      type: task.type,
      promptId: `${task.code.toLowerCase()}-v1`,
      promptText: task.prompt,
    },
    consent: {
      selfDataOnly: true,
      accepted: true,
      noticeVersion: NOTICE_VERSION,
    },
    selfReport: {
      stressLevel: questionnaire.stressLevel,
      moodLevel: questionnaire.moodLevel,
      sleepQuality: questionnaire.sleepQuality,
      note: `fatigue:${questionnaire.fatigueLevel}`,
    },
    device: {
      userAgent: navigator.userAgent,
      platform: navigator.userAgentData?.platform || navigator.platform || 'unknown',
      maxTouchPoints: navigator.maxTouchPoints || 0,
      devicePixelRatio: window.devicePixelRatio || 1,
      observedPointerTypes: pointerTypes,
      supportsPressure: pressureIsAvailable(points),
      supportsTilt: points.some(
        (point) => Number.isFinite(point.tiltX) && (point.tiltX !== 0 || point.tiltY !== 0),
      ),
    },
    canvas: snapshot.canvas,
    timing: {
      createdAt: isoFromEpoch(firstPoint?.timestampEpochMs) || new Date().toISOString(),
      startedAt: isoFromEpoch(firstPoint?.timestampEpochMs),
      endedAt: isoFromEpoch(lastPoint?.timestampEpochMs),
      durationMs: lastPoint?.elapsedMs || 0,
    },
    summary: {
      pointCount: points.length,
      strokeCount: snapshot.strokeCount,
    },
    points,
  }
}

export function buildCollectionPackage({ participantId, roundId, questionnaire, attempts }) {
  return {
    collectionSchemaVersion: '1.0.0',
    exportedAt: new Date().toISOString(),
    participantId,
    roundId,
    questionnaire: {
      completedAt: new Date().toISOString(),
      ...questionnaire,
    },
    attempts,
  }
}
