import { onBeforeUnmount, onMounted, ref } from 'vue'
import { normalizePointer } from '../domain/normalizePointer.js'

export function usePointerCapture(canvasRef, onPoint) {
  const pointCount = ref(0)
  const strokeCount = ref(0)
  const activePointerId = ref(null)
  let sequence = 0
  let startedAt = null

  function samplesFor(event) {
    if (event.type === 'pointermove' && typeof event.getCoalescedEvents === 'function') {
      const coalesced = event.getCoalescedEvents()
      if (coalesced.length) return coalesced
    }
    return [event]
  }

  function capture(event, phase) {
    const canvas = canvasRef.value
    if (!canvas) return
    if (event.pointerType === 'mouse' && event.button !== 0 && phase === 'down') return
    if (phase !== 'down' && activePointerId.value !== event.pointerId) return

    event.preventDefault()
    if (phase === 'down') {
      activePointerId.value = event.pointerId
      strokeCount.value += 1
      if (startedAt === null) startedAt = performance.now()
      canvas.setPointerCapture?.(event.pointerId)
    }

    const samples = phase === 'move' ? samplesFor(event) : [event]
    for (const sample of samples) {
      const point = normalizePointer(sample, event, canvas, {
        strokeId: strokeCount.value,
        phase,
        startedAt,
        nextSequence: () => ++sequence,
      })
      pointCount.value += 1
      onPoint(point)
    }

    if (phase === 'up') {
      canvas.releasePointerCapture?.(event.pointerId)
      activePointerId.value = null
    }
  }

  function reset() {
    pointCount.value = 0
    strokeCount.value = 0
    activePointerId.value = null
    sequence = 0
    startedAt = null
  }

  function cancelActivePointer(event) {
    if (activePointerId.value === event.pointerId) capture(event, 'up')
  }

  function preventTouchScroll(event) {
    if (event.target === canvasRef.value) event.preventDefault()
  }

  onMounted(() => document.addEventListener('touchmove', preventTouchScroll, { passive: false }))
  onBeforeUnmount(() => document.removeEventListener('touchmove', preventTouchScroll))

  return {
    pointCount,
    strokeCount,
    reset,
    onPointerDown: (event) => capture(event, 'down'),
    onPointerMove: (event) => capture(event, 'move'),
    onPointerUp: (event) => capture(event, 'up'),
    onPointerCancel: cancelActivePointer,
  }
}
