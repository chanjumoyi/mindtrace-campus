<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { usePointerCapture } from '../composables/usePointerCapture'

const props = defineProps({ taskCode: { type: String, required: true } })

const canvasRef = ref(null)
const points = ref([])
const observedPointerType = ref('等待输入')
let resizeObserver

function drawPoint(point) {
  const canvas = canvasRef.value
  if (!canvas) return
  const context = canvas.getContext('2d')
  const scale = window.devicePixelRatio || 1
  const current = { x: point.x * scale, y: point.y * scale }
  const previous = [...points.value]
    .reverse()
    .find((item) => item.strokeId === point.strokeId && item.sequence !== point.sequence)

  context.lineCap = 'round'
  context.lineJoin = 'round'
  context.strokeStyle = '#203833'
  context.lineWidth = (1.8 + (point.pressure ?? 0.35) * 2.8) * scale
  context.beginPath()
  if (previous) context.moveTo(previous.x * scale, previous.y * scale)
  else context.moveTo(current.x, current.y)
  context.lineTo(current.x, current.y)
  context.stroke()
}

function acceptPoint(point) {
  points.value.push(point)
  observedPointerType.value =
    point.pointerType === 'pen' ? '触控笔' : point.pointerType === 'touch' ? '触摸' : '鼠标'
  drawPoint(point)
}

const capture = usePointerCapture(canvasRef, acceptPoint)

const pressureStatus = computed(() => {
  const values = points.value
    .map((point) => point.pressure)
    .filter((value) => Number.isFinite(value) && value > 0)
  if (!values.length) return '未检测'
  return Math.max(...values) - Math.min(...values) >= 0.01 ? '变化正常' : '变化不足'
})

function redraw() {
  const canvas = canvasRef.value
  if (!canvas) return
  const context = canvas.getContext('2d')
  const scale = window.devicePixelRatio || 1
  context.clearRect(0, 0, canvas.width, canvas.height)
  const rendered = []
  for (const point of points.value) {
    const previous = [...rendered].reverse().find((item) => item.strokeId === point.strokeId)
    context.lineCap = 'round'
    context.lineJoin = 'round'
    context.strokeStyle = '#203833'
    context.lineWidth = (1.8 + (point.pressure ?? 0.35) * 2.8) * scale
    context.beginPath()
    if (previous) context.moveTo(previous.x * scale, previous.y * scale)
    else context.moveTo(point.x * scale, point.y * scale)
    context.lineTo(point.x * scale, point.y * scale)
    context.stroke()
    rendered.push(point)
  }
}

function resizeCanvas() {
  const canvas = canvasRef.value
  if (!canvas) return
  const rect = canvas.getBoundingClientRect()
  const scale = window.devicePixelRatio || 1
  const width = Math.max(1, Math.round(rect.width * scale))
  const height = Math.max(1, Math.round(rect.height * scale))
  if (canvas.width === width && canvas.height === height) return
  canvas.width = width
  canvas.height = height
  redraw()
}

function reset() {
  points.value = []
  observedPointerType.value = '等待输入'
  capture.reset()
  const canvas = canvasRef.value
  canvas?.getContext('2d').clearRect(0, 0, canvas.width, canvas.height)
}

function getSnapshot() {
  const canvas = canvasRef.value
  const rect = canvas.getBoundingClientRect()
  return {
    points: points.value.map((point) => ({ ...point })),
    strokeCount: capture.strokeCount.value,
    canvas: {
      width: Number(rect.width.toFixed(3)),
      height: Number(rect.height.toFixed(3)),
      background: '#fffdf7',
    },
  }
}

onMounted(async () => {
  await nextTick()
  resizeObserver = new ResizeObserver(resizeCanvas)
  resizeObserver.observe(canvasRef.value)
  resizeCanvas()
})
onBeforeUnmount(() => resizeObserver?.disconnect())

defineExpose({ getSnapshot, reset })
</script>

<template>
  <div class="canvas-wrap">
    <canvas
      ref="canvasRef"
      class="writing-canvas"
      :aria-label="`${props.taskCode} 手写区域`"
      @pointerdown="capture.onPointerDown"
      @pointermove="capture.onPointerMove"
      @pointerup="capture.onPointerUp"
      @pointercancel="capture.onPointerCancel"
    ></canvas>
    <div v-if="!points.length" class="canvas-placeholder">请在这里书写</div>
    <div class="capture-strip" aria-live="polite">
      <span>输入：{{ observedPointerType }}</span>
      <span>笔画：{{ capture.strokeCount.value }}</span>
      <span>采样点：{{ capture.pointCount.value }}</span>
      <span>压感：{{ pressureStatus }}</span>
    </div>
  </div>
</template>

<style scoped>
.canvas-wrap {
  position: relative;
  min-height: 310px;
  overflow: hidden;
  border: 1px solid #d7dfd9;
  border-radius: 18px;
  background: #fffdf7;
}
.writing-canvas {
  display: block;
  width: 100%;
  height: clamp(310px, 48vh, 480px);
  touch-action: none;
  cursor: crosshair;
}
.canvas-placeholder {
  position: absolute;
  inset: 0 0 42px;
  display: grid;
  place-items: center;
  color: #9aa8a2;
  pointer-events: none;
  font-size: 14px;
}
.capture-strip {
  position: absolute;
  left: 10px;
  right: 10px;
  bottom: 10px;
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 6px 12px;
  padding: 8px 10px;
  border-radius: 10px;
  background: rgba(241, 246, 242, 0.92);
  color: #587068;
  font-size: 11px;
  pointer-events: none;
}
</style>
