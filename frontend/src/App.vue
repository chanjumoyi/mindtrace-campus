<script setup>
import { computed, onMounted, ref } from 'vue'
import { api } from './api'

const active = ref('home')
const modules = ref([])
const mood = ref(3)
const stress = ref(3)
const note = ref('')
const chatInput = ref('')
const chatLog = ref([
  { role: 'assistant', text: '你好，我是心迹AI。你可以从今天最想说的一件事开始。' },
])
const loading = ref(false)
const message = ref('')

const nav = [
  ['home', '今日首页'],
  ['chat', 'AI 陪伴'],
  ['journal', '电子手账'],
  ['handwriting', '笔迹观察'],
  ['projective', '房树人与沙盘'],
  ['wellness', '冥想与科普'],
]

const title = computed(() => nav.find(([key]) => key === active.value)?.[1] || '心迹AI')

onMounted(async () => {
  try { modules.value = await api('/modules') } catch { modules.value = [] }
})

async function saveMood() {
  loading.value = true
  try {
    await api('/wellbeing/moods', {
      method: 'POST',
      body: JSON.stringify({ mood: mood.value, stress: stress.value, note: note.value || null }),
    })
    message.value = '今天的状态已经记录。'
    note.value = ''
  } catch (error) { message.value = error.message }
  finally { loading.value = false }
}

async function sendChat() {
  const text = chatInput.value.trim()
  if (!text || loading.value) return
  chatLog.value.push({ role: 'user', text })
  chatInput.value = ''
  loading.value = true
  try {
    const result = await api('/ai/chat', { method: 'POST', body: JSON.stringify({ message: text }) })
    chatLog.value.push({ role: 'assistant', text: result.reply, urgent: result.risk_level === 'urgent_review' })
  } catch (error) { chatLog.value.push({ role: 'assistant', text: error.message }) }
  finally { loading.value = false }
}
</script>

<template>
  <div class="shell">
    <aside>
      <a class="brand" href="#" @click.prevent="active = 'home'">
        <span class="brand-mark">心</span><span>心迹AI<small>MindLine</small></span>
      </a>
      <nav aria-label="主导航">
        <button v-for="item in nav" :key="item[0]" :class="{ active: active === item[0] }" @click="active = item[0]">
          {{ item[1] }}
        </button>
      </nav>
      <div class="privacy">你的记录默认仅自己可见。平台不提供医学诊断。</div>
    </aside>

    <main>
      <header><div><p>大学生心理健康智能交互平台</p><h1>{{ title }}</h1></div><span class="status">本地研究原型</span></header>

      <section v-if="active === 'home'" class="page">
        <div class="hero">
          <div><span class="eyebrow">今天也值得被认真对待</span><h2>从一次轻量记录开始，照顾此刻的自己。</h2><p>对话、手账与行为数据只用于支持自我觉察；高风险信息始终建议由专业人员复核。</p></div>
          <button class="primary" @click="active = 'chat'">开始聊聊</button>
        </div>
        <div class="grid two">
          <form class="card checkin" @submit.prevent="saveMood">
            <div class="section-title"><div><span>每日记录</span><h3>此刻状态</h3></div><span class="date">今天</span></div>
            <label>心情 <strong>{{ mood }}/5</strong><input v-model.number="mood" type="range" min="1" max="5" /></label>
            <label>压力 <strong>{{ stress }}/5</strong><input v-model.number="stress" type="range" min="1" max="5" /></label>
            <textarea v-model="note" placeholder="想补充些什么？（选填）" maxlength="1000"></textarea>
            <button class="primary" :disabled="loading">保存记录</button><p v-if="message" class="feedback">{{ message }}</p>
          </form>
          <div class="card">
            <div class="section-title"><div><span>项目范围</span><h3>核心能力</h3></div></div>
            <ul class="module-list"><li v-for="item in modules" :key="item.code"><span>{{ item.name }}</span><em>{{ item.stage === 'mvp' ? '核心' : '研究' }}</em></li></ul>
          </div>
        </div>
      </section>

      <section v-else-if="active === 'chat'" class="page chat-page">
        <div class="safety-banner">如你正面临紧迫的人身安全风险，请立即联系身边可信任的人、学校心理中心或当地急救服务。</div>
        <div class="chat-card">
          <div class="messages"><div v-for="(item, i) in chatLog" :key="i" :class="['bubble', item.role, { urgent: item.urgent }]">{{ item.text }}</div></div>
          <form class="chat-form" @submit.prevent="sendChat"><textarea v-model="chatInput" placeholder="写下此刻最想说的事……" maxlength="4000"></textarea><button class="primary" :disabled="loading">发送</button></form>
        </div>
      </section>

      <section v-else class="page">
        <div class="feature-intro">
          <span class="eyebrow">{{ active === 'handwriting' || active === 'projective' ? '探索性功能' : '核心功能' }}</span>
          <h2 v-if="active === 'journal'">电子手账与多维记录</h2>
          <h2 v-else-if="active === 'handwriting'">动态笔迹行为观察</h2>
          <h2 v-else-if="active === 'projective'">房树人与心理沙盘</h2>
          <h2 v-else>冥想练习与心理科普</h2>
          <p v-if="active === 'journal'">记录事件、感受和身体状态，逐步形成仅属于你的纵向趋势。</p>
          <p v-else-if="active === 'handwriting'">采集速度、停顿、轨迹与设备压力等客观特征，不据此判断人格或疾病。</p>
          <p v-else-if="active === 'projective'">AI仅辅助描述可观察元素并提出自我探索问题，不自动给出心理结论。</p>
          <p v-else>用短时练习帮助自己回到当下，并阅读经过审核的心理健康知识。</p>
        </div>
        <div class="grid three"><article class="card" v-for="n in 3" :key="n"><span class="card-index">0{{ n }}</span><h3>{{ ['轻量采集', '安全分析', '纵向反馈'][n - 1] }}</h3><p>当前目录已保留对应研究资产，并按立项阶段逐步接入。</p></article></div>
      </section>
    </main>
  </div>
</template>
