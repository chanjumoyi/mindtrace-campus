<script setup>
import { computed, nextTick, reactive, ref } from 'vue'
import WritingCanvas from '../components/WritingCanvas.vue'
import { QUESTIONNAIRE_ITEMS, WRITING_TASKS } from '../constants'
import { buildCollectionPackage, buildTrace } from '../domain/buildTrace'
import { downloadCollectionPackage, saveCollectionPackage } from '../composables/useOfflineBuffer'

const emit = defineEmits(['exit'])

const step = ref(0)
const participantId = ref(createParticipantId())
const roundId = ref('')
const consentConfirmed = ref(false)
const questionnaireIndex = ref(0)
const questionnaire = reactive({})
const writingTaskIndex = ref(0)
const canvasRef = ref(null)
const attempts = ref([])
const errorMessage = ref('')
const saving = ref(false)
const completedPackage = ref(null)

const currentQuestion = computed(() => QUESTIONNAIRE_ITEMS[questionnaireIndex.value])
const currentTask = computed(() => WRITING_TASKS[writingTaskIndex.value])
const mainProgress = computed(() => Math.max(0, Math.min(100, ((step.value - 1) / 3) * 100)))
const participantIdValid = computed(() => /^[a-zA-Z0-9_-]{1,40}$/.test(participantId.value))

function createParticipantId() {
  return `P-${crypto.randomUUID().slice(0, 8).toUpperCase()}`
}

function nextRoundFor(id) {
  const safeId = id.replace(/[^a-zA-Z0-9_-]/g, '')
  const previous = Number(localStorage.getItem(`mindline-round:${safeId}`) || 0)
  return `R-${String(previous + 1).padStart(3, '0')}`
}

function begin() {
  step.value = 1
  roundId.value = nextRoundFor(participantId.value)
}

function continueFromIdentity() {
  errorMessage.value = ''
  if (!participantIdValid.value) {
    errorMessage.value = '编号只能包含字母、数字、短横线或下划线，最多 40 个字符。'
    return
  }
  if (!consentConfirmed.value) {
    errorMessage.value = '请先确认参与者已经完成线下知情同意。'
    return
  }
  roundId.value = nextRoundFor(participantId.value)
  step.value = 2
}

function selectAnswer(value) {
  questionnaire[currentQuestion.value.id] = value
  errorMessage.value = ''
}

function nextQuestion() {
  if (questionnaire[currentQuestion.value.id] == null) {
    errorMessage.value = '请选择一个选项后继续。'
    return
  }
  errorMessage.value = ''
  if (questionnaireIndex.value < QUESTIONNAIRE_ITEMS.length - 1) {
    questionnaireIndex.value += 1
    return
  }
  step.value = 3
}

function previousQuestion() {
  errorMessage.value = ''
  if (questionnaireIndex.value > 0) questionnaireIndex.value -= 1
  else step.value = 1
}

async function confirmWriting() {
  errorMessage.value = ''
  const snapshot = canvasRef.value?.getSnapshot()
  if (!snapshot || snapshot.points.length < 3) {
    errorMessage.value = '还没有采集到足够的轨迹，请在书写区完成当前任务。'
    return
  }
  if (currentTask.value.code === 'PRESS_CHECK' && snapshot.strokeCount < 3) {
    errorMessage.value = '压感检查需要画三条独立的短横线。'
    return
  }
  attempts.value.push(
    buildTrace({
      participantId: participantId.value,
      task: currentTask.value,
      questionnaire,
      snapshot,
    }),
  )

  if (writingTaskIndex.value < WRITING_TASKS.length - 1) {
    writingTaskIndex.value += 1
    await nextTick()
    canvasRef.value?.reset()
    return
  }
  await finishCollection()
}

async function finishCollection() {
  saving.value = true
  try {
    const payload = {
      recordId: crypto.randomUUID(),
      ...buildCollectionPackage({
        participantId: participantId.value,
        roundId: roundId.value,
        questionnaire: { ...questionnaire },
        attempts: attempts.value.map((trace) => JSON.parse(JSON.stringify(trace))),
      }),
    }
    await saveCollectionPackage(payload)
    localStorage.setItem(
      `mindline-round:${participantId.value}`,
      String(Number(roundId.value.split('-')[1])),
    )
    completedPackage.value = payload
    downloadCollectionPackage(payload)
    step.value = 4
  } catch {
    errorMessage.value = '当前设备无法保存数据，请检查浏览器存储权限后重试。'
  } finally {
    saving.value = false
  }
}

function clearCanvas() {
  errorMessage.value = ''
  canvasRef.value?.reset()
}

function downloadAgain() {
  if (completedPackage.value) downloadCollectionPackage(completedPackage.value)
}

function restart() {
  step.value = 1
  roundId.value = nextRoundFor(participantId.value)
  questionnaireIndex.value = 0
  writingTaskIndex.value = 0
  attempts.value = []
  completedPackage.value = null
  errorMessage.value = ''
  for (const key of Object.keys(questionnaire)) delete questionnaire[key]
}
</script>

<template>
  <div class="collector-page">
    <button class="exit-button" type="button" @click="emit('exit')">返回心迹AI</button>

    <div v-if="step > 0 && step < 4" class="flow-status">
      <div class="flow-status__row">
        <span>线下手写采集</span>
        <strong>步骤 {{ step }}/3</strong>
      </div>
      <div class="flow-progress"><span :style="{ width: `${mainProgress}%` }"></span></div>
    </div>

    <section v-if="step === 0" class="collector-card intro-card">
      <span class="step-kicker">01 · 采集者页</span>
      <div class="intro-mark" aria-hidden="true">迹</div>
      <h1>手写行为采集</h1>
      <p>依次完成状态记录、固定抄写与自由书写。数据仅用于研究中的客观行为观察。</p>
      <button class="main-action" type="button" @click="begin">开始采集</button>
      <small>预计用时 5～8 分钟 · 支持触控笔、触摸和鼠标</small>
    </section>

    <section v-else-if="step === 1" class="collector-card identity-card">
      <span class="step-kicker">02 · 参与者识别</span>
      <h1>确认本次采集信息</h1>
      <p class="section-copy">编号可以修改；轮次会根据该编号在当前设备上的记录自动顺延。</p>

      <label class="field-label" for="participant-id">匿名参与者编号</label>
      <input
        id="participant-id"
        v-model.trim="participantId"
        class="text-input"
        maxlength="40"
        autocomplete="off"
        @input="roundId = nextRoundFor(participantId)"
      />

      <label class="field-label" for="round-id">采集轮次</label>
      <input id="round-id" :value="roundId" class="text-input muted" readonly />

      <label class="consent-check">
        <input v-model="consentConfirmed" type="checkbox" />
        <span>已确认参与者完成线下知情同意，且本页未填写姓名、学号或联系方式。</span>
      </label>

      <p v-if="errorMessage" class="form-error" role="alert">{{ errorMessage }}</p>
      <button class="main-action" type="button" @click="continueFromIdentity">进入状态记录</button>
    </section>

    <section v-else-if="step === 2" class="collector-card questionnaire-card">
      <div class="question-meta">
        <span class="step-kicker">03 · 状态记录</span>
        <strong>{{ questionnaireIndex + 1 }}/{{ QUESTIONNAIRE_ITEMS.length }}</strong>
      </div>
      <div class="question-progress">
        <span
          :style="{ width: `${((questionnaireIndex + 1) / QUESTIONNAIRE_ITEMS.length) * 100}%` }"
        ></span>
      </div>
      <h1>{{ currentQuestion.title }}</h1>
      <p class="section-copy">{{ currentQuestion.hint }}</p>

      <div class="scale-options" role="radiogroup" :aria-label="currentQuestion.title">
        <button
          v-for="value in currentQuestion.max"
          :key="value"
          type="button"
          role="radio"
          :class="['scale-option', { selected: questionnaire[currentQuestion.id] === value }]"
          :aria-checked="questionnaire[currentQuestion.id] === value"
          @click="selectAnswer(value)"
        >
          <span>{{ value }}</span>
        </button>
      </div>
      <div class="scale-labels">
        <span>{{ currentQuestion.lowLabel }}</span>
        <span>{{ currentQuestion.highLabel }}</span>
      </div>

      <p v-if="errorMessage" class="form-error" role="alert">{{ errorMessage }}</p>
      <div class="bottom-actions">
        <button class="secondary-action" type="button" @click="previousQuestion">上一步</button>
        <button class="main-action compact" type="button" @click="nextQuestion">
          {{ questionnaireIndex === QUESTIONNAIRE_ITEMS.length - 1 ? '开始书写' : '下一题' }}
        </button>
      </div>
    </section>

    <section v-else-if="step === 3" class="collector-card writing-card">
      <div class="question-meta">
        <span class="step-kicker">04 · 书写采集</span>
        <strong>任务 {{ writingTaskIndex + 1 }}/{{ WRITING_TASKS.length }}</strong>
      </div>
      <div class="question-progress">
        <span
          :style="{ width: `${((writingTaskIndex + 1) / WRITING_TASKS.length) * 100}%` }"
        ></span>
      </div>
      <h1>{{ currentTask.title }}</h1>
      <div class="task-prompt">
        <span>题目</span>
        <strong>{{ currentTask.prompt }}</strong>
        <p>{{ currentTask.guidance }}</p>
      </div>

      <WritingCanvas ref="canvasRef" :key="currentTask.code" :task-code="currentTask.code" />

      <p v-if="errorMessage" class="form-error" role="alert">{{ errorMessage }}</p>
      <div class="bottom-actions">
        <button class="secondary-action" type="button" @click="clearCanvas">清空重写</button>
        <button
          class="main-action compact"
          type="button"
          :disabled="saving"
          @click="confirmWriting"
        >
          {{
            saving
              ? '正在保存…'
              : writingTaskIndex === WRITING_TASKS.length - 1
                ? '确认并保存'
                : '确认本题'
          }}
        </button>
      </div>
    </section>

    <section v-else class="collector-card success-card">
      <span class="step-kicker">采集完成</span>
      <div class="success-mark" aria-hidden="true">完成</div>
      <h1>本轮数据已安全保存</h1>
      <p>
        已在当前设备保存 {{ attempts.length }} 份书写轨迹，并下载 JSON 备份。编号为
        <strong>{{ participantId }}</strong
        >，轮次为 <strong>{{ roundId }}</strong
        >。
      </p>
      <button class="main-action" type="button" @click="downloadAgain">再次下载 JSON</button>
      <button class="secondary-action wide" type="button" @click="restart">继续下一轮采集</button>
    </section>
  </div>
</template>

<style scoped src="../collector.css"></style>
