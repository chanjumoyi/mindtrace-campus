import { api, session } from './api.js';
import { runTrackedAnalysis } from './analysis-workflow.mjs';
import { escapeHtml, pageHeader, toast } from './components.js';

const SANDPLAY_ITEMS = [
  ['person', '人物', '🧑'], ['family', '家庭', '👨‍👩‍👧'], ['house', '房屋', '🏠'],
  ['tree', '树木', '🌳'], ['flower', '花朵', '🌻'], ['dog', '动物', '🐕'],
  ['bird', '飞鸟', '🕊️'], ['mountain', '山峰', '⛰️'], ['river', '河流', '🌊'],
  ['sun', '太阳', '☀️'], ['car', '车辆', '🚙'], ['bridge', '桥梁', '🌉']
];

const sandplayState = { elements: [], nextId: 1 };
const assistantState = {
  messages: [{ role: 'assistant', text: '你好，我是心迹AI助手。你可以从笔迹、沙盘或房树人工作台带着结构化结果来继续探索。当前输出仅用于自我观察，不构成诊断。' }]
};
let htpPreviewUrl = '';
window.__mindlineContexts = window.__mindlineContexts || {};

const htpDrawState = {
  canvas: null,
  ctx: null,
  undoStack: [],
  tool: 'pen',
  drawing: false,
  hasContent: false
};

export async function studioHomePage() {
  return `<div class="content studio-home">
    ${pageHeader('心迹AI 综合工作台', `欢迎回来，${session.user?.displayName || '同学'}`, '<span class="studio-pill">本地演示环境</span>')}
    <section class="studio-hero card">
      <div><span class="studio-kicker">MINDLINE · MULTIMODAL WELLBEING</span><h2>把表达、观察与行动放在同一条路径里</h2><p>从动态笔迹、心理沙盘或房树人开始，系统只记录可观察特征，再通过统一AI网关生成克制的探索问题和后续任务。</p><div class="studio-actions"><a class="btn btn-primary" href="#/handwriting-live">开始书写</a><a class="btn" href="#/sandplay">进入沙盘</a></div></div>
      <div class="studio-orbit" aria-hidden="true"><span>笔迹</span><span>沙盘</span><span>HTP</span><strong>心迹AI</strong></div>
    </section>
    <section class="studio-flow" aria-label="产品流程">
      ${flowStep('01','自主表达','书写、布局或上传图像')}${flowStep('02','客观观察','轨迹、几何与问卷特征')}${flowStep('03','AI辅助','引用、限制与探索问题')}${flowStep('04','行动反馈','任务、复评与审计记录')}
    </section>
    <section class="section"><div class="studio-section-title"><div><span>核心能力</span><h2>选择一个工作台</h2></div><p>每个模块共享同一登录、文件、任务、AI网关与审计底座。</p></div>
      <div class="studio-module-grid">
        ${moduleCard('✍️','动态笔迹','直接使用数位笔书写，记录压力、倾角、速度和停顿。','#/handwriting-live','A · 可运行','ready')}
        ${moduleCard('🧭','轨迹报告','导入采集JSON，查看特征、实验基线、引用与限制。','#/handwriting','A · 可运行','ready')}
        ${moduleCard('🏝️','心理沙盘','摆放元素并计算类别、象限、中心度和布局结构。','#/sandplay','B · 本地观察','progress')}
        ${moduleCard('🏡','房树人 HTP','上传作品、补充结构化问卷并生成非诊断性观察。','#/htp','B · 轻量闭环','progress')}
        ${moduleCard('💬','AI陪伴助手','通过统一AI网关承接各模块上下文和探索问题。','#/assistant','Agent · 可替换','progress')}
        ${moduleCard('✅','行动任务','把探索建议转为可跟踪任务和反馈。','#/tasks','C · 可运行','ready')}
      </div>
    </section>
    <section class="section studio-status-grid">
      <article class="card studio-status"><span class="status-dot" id="handwriting-health-dot"></span><div><strong>笔迹分析服务</strong><p id="handwriting-health-text">正在检查 8091 服务…</p></div></article>
      <article class="card studio-status"><span class="status-dot ready"></span><div><strong>公共 Java 网关</strong><p>当前会话与统一API连接正常</p></div></article>
      <article class="card studio-status"><span class="status-dot warning"></span><div><strong>安全边界</strong><p>结果仅用于自我观察，不用于诊断或个体决策</p></div></article>
    </section>
  </div>`;
}

export function bindStudioHomePage() {
  checkHandwritingHealth();
}

export async function handwritingLivePage() {
  const collectorUrl = handwritingServiceUrl('/collector/');
  return `<div class="content studio-page">
    ${pageHeader('动态笔迹书写', '在统一工作台中直接使用数位笔完成采集和一键分析。', `<a class="btn" href="#/handwriting">导入历史轨迹</a><a class="btn btn-primary" href="${escapeHtml(collectorUrl)}" target="_blank" rel="noreferrer">全屏打开</a>`)}
    <div class="scope-note"><strong>数据说明：</strong>页面记录书写位置、时间、压力和倾角；分析只描述本次书写行为，不推断人格或疾病。</div>
    <section class="card studio-service-bar"><div><span class="status-dot" id="live-health-dot"></span><strong id="live-health-text">正在连接笔迹服务…</strong></div><span class="code">${escapeHtml(collectorUrl)}</span></section>
    <section class="card studio-embed"><iframe id="handwriting-live-frame" title="心迹AI动态笔迹采集器" src="${escapeHtml(collectorUrl)}" loading="eager"></iframe></section>
  </div>`;
}

export function bindHandwritingLivePage() {
  checkHandwritingHealth('live-health-dot', 'live-health-text');
}

export async function sandplayPage() {
  const history = await loadAnalysisHistory('SANDPLAY');
  return `<div class="content studio-page">
    ${pageHeader('心理沙盘工作台', '自由摆放元素，系统只生成结构化布局观察。', '<button class="btn" id="sand-undo">撤销</button><button class="btn btn-danger" id="sand-clear">清空</button>')}
    <div class="scope-note"><strong>使用边界：</strong>元素选择和空间位置没有固定心理含义；任何说明都需要结合用户自己的叙述。</div>
    <section class="sand-layout">
      <aside class="card sand-palette"><h2>元素库</h2><p class="muted">点击元素添加到画布，再拖动调整位置。</p><div class="sand-palette-grid">${SANDPLAY_ITEMS.map(([type,label,icon]) => `<button class="sand-palette-item" data-type="${type}" data-label="${label}" data-icon="${icon}" type="button"><span>${icon}</span>${label}</button>`).join('')}</div></aside>
      <div class="sand-main"><div class="card sand-board-wrap"><div class="sand-axis sand-axis-x"></div><div class="sand-axis sand-axis-y"></div><div id="sand-board" class="sand-board" aria-label="沙盘画布"></div><span class="sand-quadrant q1">远景 · 左</span><span class="sand-quadrant q2">远景 · 右</span><span class="sand-quadrant q3">近景 · 左</span><span class="sand-quadrant q4">近景 · 右</span></div>
        <div class="studio-actions"><button class="btn btn-primary" id="sand-analyze" type="button">生成结构化观察</button><span class="muted" id="sand-count">0 个元素</span></div>
        <section id="sand-result" class="studio-result" aria-live="polite"></section>
      </div>
    </section>
    <section id="sand-history" class="section">${renderAnalysisHistory(history, 'SANDPLAY')}</section>
  </div>`;
}

export function bindSandplayPage() {
  renderSandplay();
  document.querySelectorAll('.sand-palette-item').forEach(button => button.addEventListener('click', () => {
    const offset = sandplayState.elements.length % 7;
    sandplayState.elements.push({ id: sandplayState.nextId++, type: button.dataset.type, label: button.dataset.label, icon: button.dataset.icon, x: 38 + offset * 8, y: 42 + (offset % 3) * 10 });
    renderSandplay();
  }));
  document.querySelector('#sand-undo')?.addEventListener('click', () => { sandplayState.elements.pop(); renderSandplay(); });
  document.querySelector('#sand-clear')?.addEventListener('click', () => { if (confirm('确定清空当前沙盘吗？')) { sandplayState.elements = []; renderSandplay(); } });
  document.querySelector('#sand-analyze')?.addEventListener('click', analyzeSandplay);
  bindAnalysisHistory('sand-history', 'SANDPLAY');
}

export async function htpPage() {
  const history = await loadAnalysisHistory('HTP');
  return `<div class="content studio-page">
    ${pageHeader('房树人 HTP 工作台', '上传作品或现场绘制，补充创作说明，生成可追溯的客观观察。')}
    <div class="scope-note"><strong>重要：</strong>房树人不能用于自动诊断。当前版本优先记录图像元数据和用户自述，视觉模型接入后仍必须遵循"观察与解释分离"。</div>
    <section class="htp-layout">
      <form id="htp-form" class="card section-card htp-form">
        <h2>作品与问卷</h2>
        <div class="htp-mode-tabs">
          <button type="button" class="htp-mode-tab active" data-mode="upload">上传图片</button>
          <button type="button" class="htp-mode-tab" data-mode="draw">现场绘制</button>
        </div>
        <div id="htp-upload-panel" class="htp-mode-panel">
          <label class="htp-upload" for="htp-file"><input id="htp-file" name="file" type="file" accept="image/png,image/jpeg"><span>选择 PNG/JPEG 作品</span><small>文件将通过统一文件中心保存并生成审计记录</small></label>
        </div>
        <div id="htp-draw-panel" class="htp-mode-panel" hidden>
          <div class="htp-draw-toolbar">
            <button type="button" class="htp-tool-btn active" data-tool="pen" title="黑色画笔">✏️ 画笔</button>
            <button type="button" class="htp-tool-btn" data-tool="eraser" title="橡皮擦">🧹 橡皮</button>
            <button type="button" class="htp-tool-btn" id="htp-undo-btn" title="撤回">↩️ 撤回</button>
            <button type="button" class="htp-tool-btn htp-clear-btn" id="htp-clear-btn" title="清空画布">🗑️ 清空</button>
          </div>
          <div class="htp-canvas-wrap">
            <canvas id="htp-canvas" width="700" height="500"></canvas>
            <span id="htp-canvas-placeholder">在此区域按住鼠标左键绘制</span>
          </div>
        </div>
        <div class="field"><label>这幅画讲述了什么？</label><textarea name="story" maxlength="500" placeholder="请用自己的语言描述作品…" required></textarea></div>
        <div class="field"><label>房屋描述</label><input name="houseDescription" maxlength="180" placeholder="例如：房屋是谁居住、周围环境如何"></div>
        <div class="field"><label>树木描述</label><input name="treeDescription" maxlength="180" placeholder="例如：树的种类、季节、状态"></div>
        <div class="field"><label>人物描述</label><input name="personDescription" maxlength="180" placeholder="例如：人物是谁、正在做什么"></div>
        <label class="check-row"><input name="consent" type="checkbox" required>我理解结果仅用于自我探索，并同意在演示环境处理这份模拟/匿名作品。</label>
        <button class="btn btn-primary" type="submit">保存并生成观察</button>
      </form>
      <div><section class="card htp-preview"><div id="htp-placeholder"><strong>作品预览</strong><p>选择文件或绘制后将在这里显示。</p></div><img id="htp-preview-image" alt="房树人作品预览" hidden></section><section id="htp-result" class="studio-result" aria-live="polite"></section></div>
    </section>
    <section id="htp-history" class="section">${renderAnalysisHistory(history, 'HTP')}</section>
  </div>`;
}

export function bindHtpPage() {
  const input = document.querySelector('#htp-file');
  const filePanel = document.querySelector('#htp-upload-panel');
  const drawPanel = document.querySelector('#htp-draw-panel');
  const placeholder = document.querySelector('#htp-placeholder');
  const previewImage = document.querySelector('#htp-preview-image');
  const canvas = document.querySelector('#htp-canvas');
  const canvasPlaceholder = document.querySelector('#htp-canvas-placeholder');

  // Mode tabs
  document.querySelectorAll('.htp-mode-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.htp-mode-tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      const mode = tab.dataset.mode;
      if (mode === 'upload') {
        filePanel.hidden = false;
        drawPanel.hidden = true;
        input.required = true;
      } else {
        filePanel.hidden = true;
        drawPanel.hidden = false;
        input.required = false;
        initCanvas();
      }
    });
  });

  // File upload preview
  input?.addEventListener('change', () => {
    if (htpPreviewUrl) URL.revokeObjectURL(htpPreviewUrl);
    if (!canvas || !htpDrawState.hasContent) {
      // Only clear canvas-based preview if we're in upload mode
    }
    const file = input.files?.[0];
    if (!file || !previewImage) return;
    htpPreviewUrl = URL.createObjectURL(file);
    previewImage.src = htpPreviewUrl;
    previewImage.hidden = false;
    placeholder?.setAttribute('hidden', '');
    if (canvasPlaceholder) canvasPlaceholder.hidden = true;
  });

  // Canvas initialization
  function initCanvas() {
    const c = document.querySelector('#htp-canvas');
    if (!c) return;
    htpDrawState.canvas = c;
    htpDrawState.ctx = c.getContext('2d');
    htpDrawState.undoStack = [];
    htpDrawState.hasContent = false;
    htpDrawState.tool = 'pen';

    // Set initial white background
    const ctx = htpDrawState.ctx;
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, c.width, c.height);

    // Tool buttons
    document.querySelectorAll('.htp-tool-btn[data-tool]').forEach(btn => {
      btn.classList.remove('active');
      if (btn.dataset.tool === 'pen') btn.classList.add('active');
    });

    bindCanvasEvents();
  }

  function bindCanvasEvents() {
    const c = document.querySelector('#htp-canvas');
    if (!c) return;

    // Clear canvas state
    htpDrawState.canvas = c;
    htpDrawState.ctx = c.getContext('2d');
    htpDrawState.undoStack = [];
    htpDrawState.hasContent = false;
    htpDrawState.ctx.fillStyle = '#ffffff';
    htpDrawState.ctx.fillRect(0, 0, c.width, c.height);

    // Remove old listeners by cloning
    const newCanvas = c.cloneNode(true);
    c.parentNode.replaceChild(newCanvas, c);
    htpDrawState.canvas = newCanvas;
    htpDrawState.ctx = newCanvas.getContext('2d');
    // Restore white background
    htpDrawState.ctx.fillStyle = '#ffffff';
    htpDrawState.ctx.fillRect(0, 0, newCanvas.width, newCanvas.height);

    newCanvas.addEventListener('pointerdown', e => {
      if (e.button !== 0) return; // left button only
      e.preventDefault();
      htpDrawState.drawing = true;

      // Save state for undo
      const imageData = htpDrawState.ctx.getImageData(0, 0, newCanvas.width, newCanvas.height);
      htpDrawState.undoStack.push(imageData);
      if (htpDrawState.undoStack.length > 50) htpDrawState.undoStack.shift();

      const rect = newCanvas.getBoundingClientRect();
      const scaleX = newCanvas.width / rect.width;
      const scaleY = newCanvas.height / rect.height;
      const x = (e.clientX - rect.left) * scaleX;
      const y = (e.clientY - rect.top) * scaleY;

      htpDrawState.ctx.beginPath();
      htpDrawState.ctx.moveTo(x, y);
      htpDrawState.ctx.lineCap = 'round';
      htpDrawState.ctx.lineJoin = 'round';

      if (htpDrawState.tool === 'eraser') {
        htpDrawState.ctx.strokeStyle = '#ffffff';
        htpDrawState.ctx.lineWidth = 24;
      } else {
        htpDrawState.ctx.strokeStyle = '#000000';
        htpDrawState.ctx.lineWidth = 3;
      }

      // Hide placeholder on first draw
      if (!htpDrawState.hasContent) {
        htpDrawState.hasContent = true;
        if (canvasPlaceholder) canvasPlaceholder.hidden = true;
      }
    });

    newCanvas.addEventListener('pointermove', e => {
      if (!htpDrawState.drawing) return;
      e.preventDefault();
      const rect = newCanvas.getBoundingClientRect();
      const scaleX = newCanvas.width / rect.width;
      const scaleY = newCanvas.height / rect.height;
      const x = (e.clientX - rect.left) * scaleX;
      const y = (e.clientY - rect.top) * scaleY;

      htpDrawState.ctx.lineTo(x, y);
      htpDrawState.ctx.stroke();
    });

    newCanvas.addEventListener('pointerup', () => {
      htpDrawState.drawing = false;
      updateCanvasPreview();
    });

    newCanvas.addEventListener('pointerleave', () => {
      htpDrawState.drawing = false;
    });

    // Tool buttons
    document.querySelectorAll('.htp-tool-btn[data-tool]').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.htp-tool-btn[data-tool]').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        htpDrawState.tool = btn.dataset.tool;
      });
    });

    // Undo button
    document.querySelector('#htp-undo-btn')?.addEventListener('click', () => {
      if (htpDrawState.undoStack.length === 0) return;
      const imageData = htpDrawState.undoStack.pop();
      htpDrawState.ctx.putImageData(imageData, 0, 0);
      htpDrawState.hasContent = htpDrawState.undoStack.length > 0 || !isCanvasBlank();
      updateCanvasPreview();
    });

    // Clear button
    document.querySelector('#htp-clear-btn')?.addEventListener('click', () => {
      if (!htpDrawState.hasContent) return;
      if (!confirm('确定清空画布吗？')) return;
      htpDrawState.undoStack = [];
      htpDrawState.ctx.fillStyle = '#ffffff';
      htpDrawState.ctx.fillRect(0, 0, newCanvas.width, newCanvas.height);
      htpDrawState.hasContent = false;
      if (canvasPlaceholder) canvasPlaceholder.hidden = false;
      if (previewImage) previewImage.hidden = true;
      if (placeholder) placeholder.removeAttribute('hidden');
    });
  }

  function isCanvasBlank() {
    const c = htpDrawState.canvas;
    if (!c) return true;
    const ctx = htpDrawState.ctx;
    const data = ctx.getImageData(0, 0, c.width, c.height).data;
    for (let i = 0; i < data.length; i += 4) {
      if (data[i] !== 255 || data[i + 1] !== 255 || data[i + 2] !== 255) return false;
    }
    return true;
  }

  function updateCanvasPreview() {
    if (!htpDrawState.canvas || !previewImage) return;
    if (!htpDrawState.hasContent) return;
    htpDrawState.canvas.toBlob(blob => {
      if (!blob) return;
      if (htpPreviewUrl) URL.revokeObjectURL(htpPreviewUrl);
      htpPreviewUrl = URL.createObjectURL(blob);
      previewImage.src = htpPreviewUrl;
      previewImage.hidden = false;
      if (placeholder) placeholder.setAttribute('hidden', '');
    }, 'image/png');
  }

  document.querySelector('#htp-form')?.addEventListener('submit', analyzeHtp);
  bindAnalysisHistory('htp-history', 'HTP');
}

export async function assistantPage() {
  return `<div class="content studio-page assistant-page">
    ${pageHeader('AI陪伴助手', '承接笔迹、沙盘和房树人的结构化结果；真实Agent未配置时使用安全本地回复。')}
    <div class="assistant-shell card"><aside class="assistant-context"><span class="studio-kicker">探索入口</span><h2>从一个问题开始</h2>${['我想回顾今天的书写体验','帮我整理沙盘中的布局','我想描述这幅画的故事','给我一个三分钟放松任务'].map(text => `<button class="assistant-prompt" data-message="${text}" type="button">${text}</button>`).join('')}<div class="notice">如有立即伤害自己或他人的风险，请优先联系当地急救、可信任的人或专业机构。</div></aside><div class="assistant-chat"><div id="assistant-messages" class="assistant-messages"></div><form id="assistant-form" class="assistant-compose"><textarea name="message" rows="2" maxlength="1200" placeholder="写下你此刻想探索的内容…" required></textarea><button class="btn btn-primary" type="submit">发送</button></form></div></div>
  </div>`;
}

export function bindAssistantPage() {
  renderAssistantMessages();
  document.querySelectorAll('.assistant-prompt').forEach(button => button.addEventListener('click', () => sendAssistantMessage(button.dataset.message)));
  document.querySelector('#assistant-form')?.addEventListener('submit', event => {
    event.preventDefault(); const form = new FormData(event.currentTarget); const message = String(form.get('message') || '').trim();
    if (message) { event.currentTarget.reset(); sendAssistantMessage(message); }
  });
}

function flowStep(number, title, detail) { return `<article><span>${number}</span><div><strong>${title}</strong><p>${detail}</p></div></article>`; }
function moduleCard(icon, title, detail, href, meta, status) { return `<a class="card studio-module" href="${href}"><span class="studio-module-icon">${icon}</span><div><h3>${title}</h3><p>${detail}</p><small class="${status}">${meta}</small></div><b>→</b></a>`; }

function handwritingServiceUrl(path) { return `${location.protocol}//${location.hostname}:8091${path}`; }
async function checkHandwritingHealth(dotId = 'handwriting-health-dot', textId = 'handwriting-health-text') {
  const dot = document.querySelector(`#${dotId}`); const text = document.querySelector(`#${textId}`);
  try {
    const response = await fetch(handwritingServiceUrl('/api/v1/health')); if (!response.ok) throw new Error(); const health = await response.json();
    dot?.classList.add('ready'); if (text) text.textContent = `服务在线 · ${health.llm?.provider || 'mock'} / ${health.llm?.model || '未配置模型'}`;
  } catch { dot?.classList.add('error'); if (text) text.textContent = '8091 服务未连接，请先启动笔迹分析服务'; }
}

function renderSandplay() {
  const board = document.querySelector('#sand-board'); if (!board) return;
  board.innerHTML = sandplayState.elements.map(item => `<button class="sand-item" data-id="${item.id}" style="left:${item.x}%;top:${item.y}%" title="拖动${escapeHtml(item.label)}"><span>${item.icon}</span><small>${escapeHtml(item.label)}</small></button>`).join('');
  const count = document.querySelector('#sand-count'); if (count) count.textContent = `${sandplayState.elements.length} 个元素`;
  board.querySelectorAll('.sand-item').forEach(bindSandItem);
}

function bindSandItem(itemElement) {
  itemElement.addEventListener('pointerdown', event => {
    event.preventDefault(); itemElement.setPointerCapture?.(event.pointerId); const id = Number(itemElement.dataset.id); const item = sandplayState.elements.find(value => value.id === id); const board = itemElement.parentElement;
    const move = moveEvent => { const rect = board.getBoundingClientRect(); item.x = clamp((moveEvent.clientX - rect.left) / rect.width * 100, 3, 97); item.y = clamp((moveEvent.clientY - rect.top) / rect.height * 100, 5, 95); itemElement.style.left = `${item.x}%`; itemElement.style.top = `${item.y}%`; };
    const up = () => { itemElement.removeEventListener('pointermove', move); itemElement.removeEventListener('pointerup', up); };
    itemElement.addEventListener('pointermove', move); itemElement.addEventListener('pointerup', up);
  });
  itemElement.addEventListener('dblclick', () => { sandplayState.elements = sandplayState.elements.filter(item => item.id !== Number(itemElement.dataset.id)); renderSandplay(); });
}

async function analyzeSandplay(event) {
  const button = event.currentTarget; const result = document.querySelector('#sand-result');
  if (!sandplayState.elements.length) return toast('请先添加至少一个沙盘元素', 'error');
  setButtonBusy(button, true, '分析中…');
  const metrics = sandplayMetrics(); result.innerHTML = renderObservation('本地结构化观察', metrics.observations, '正在通过统一AI网关记录本次分析…');
  try {
    const sourceRef = `sandplay:${crypto.randomUUID()}`;
    const workflow = await runTrackedAnalysis({
      api,
      taskType: 'SANDPLAY_ANALYSIS',
      title: '心理沙盘结构化观察',
      requestRef: sourceRef,
      invoke: () => invokeGateway('sandplay.analyze', { elements: sandplayState.elements, metrics }),
      persist: ({ gateway, task }) => saveAnalysisRecord({
        moduleType: 'SANDPLAY', taskId: task.id, sourceRef, title: '心理沙盘结构化观察',
        observations: metrics.observations, features: sandplayFeatures(metrics),
        aiSummary: extractGatewayText(gateway), ...gatewayMetadata(gateway)
      })
    });
    const { gateway, task, record } = workflow;
    const aiSummary = extractGatewayText(gateway);
    window.__mindlineContexts.sandplay = { elements: sandplayState.elements, metrics, aiSummary, taskId: task.id, recordId: record.id, time: new Date().toLocaleString() };
    const extra = aiSummary ? `<div class="card" style="margin-top:12px;padding:14px"><strong>千问辅助说明</strong><p style="margin:8px 0 0;white-space:pre-wrap">${escapeHtml(aiSummary)}</p></div>` : '';
    result.innerHTML = renderObservation('沙盘结构化观察', metrics.observations, gatewayNote(gateway, task, record)) + extra;
    await refreshAnalysisHistory('sand-history', 'SANDPLAY');
  } catch (error) {
    const taskNote = error.taskId ? `失败任务 ${error.taskId} 已保留，可在任务状态页查看。` : '任务记录创建失败。';
    result.innerHTML = renderObservation('沙盘结构化观察', metrics.observations, `AI网关暂不可用：${escapeHtml(error.message)}。本地观察仍然有效。${taskNote}`);
  }
  finally { setButtonBusy(button, false); }
}

function sandplayMetrics() {
  const categories = {}; const quadrants = [0,0,0,0]; let center = 0;
  sandplayState.elements.forEach(item => { categories[item.label] = (categories[item.label] || 0) + 1; const right = item.x >= 50; const bottom = item.y >= 50; quadrants[(bottom ? 2 : 0) + (right ? 1 : 0)] += 1; if (Math.abs(item.x - 50) <= 18 && Math.abs(item.y - 50) <= 18) center += 1; });
  const categoryText = Object.entries(categories).map(([key,value]) => `${key}${value}`).join('、'); const occupied = quadrants.filter(Boolean).length;
  return { count: sandplayState.elements.length, categories, quadrants, centerRatio: center / sandplayState.elements.length, observations: [
    `当前沙盘包含 ${sandplayState.elements.length} 个元素：${categoryText}。`,
    `元素分布覆盖 ${occupied} 个象限，四个区域数量依次为 ${quadrants.join(' / ')}。`,
    `中心区域元素占比为 ${Math.round(center / sandplayState.elements.length * 100)}%。`,
    '以上只描述空间布局，不为元素或位置赋予固定心理含义。'
  ] };
}

async function analyzeHtp(event) {
  event.preventDefault(); const button = event.submitter; const form = event.currentTarget; const fileInput = form.querySelector('#htp-file'); const drawPanel = document.querySelector('#htp-draw-panel');
  const isDrawMode = drawPanel && !drawPanel.hidden;
  const result = document.querySelector('#htp-result');

  let file;
  if (isDrawMode) {
    // Convert canvas to file
    if (!htpDrawState.hasContent) return toast('请先在画布上绘制作品', 'error');
    const blob = await new Promise(resolve => htpDrawState.canvas.toBlob(resolve, 'image/png'));
    if (!blob) return toast('无法导出画布内容', 'error');
    file = new File([blob], `htp-drawing-${Date.now()}.png`, { type: 'image/png' });
  } else {
    file = fileInput?.files?.[0];
  }
  if (!file) return toast('请选择作品图片或切换到绘制模式', 'error');
  setButtonBusy(button, true, '处理中…');
  try {
    const metadata = await imageMetadata(file); const upload = new FormData(); upload.append('file', file);
    const saved = await api('/files?moduleCode=MULTIMODAL_AGENT&sensitivityLevel=L2', { method:'POST', body:upload }); const fields = Object.fromEntries(new FormData(form)); delete fields.file; delete fields.consent;
    const observations = [`已保存匿名作品（${metadata.width} × ${metadata.height}，${formatBytes(file.size)}${isDrawMode ? '，现场绘制' : ''}）。`, `用户故事共 ${String(fields.story || '').length} 个字符，并分别补充了房屋、树木和人物说明。`, '当前轻量版本不根据图形位置、大小或笔触自动推断人格与心理状态。'];
    const workflow = await runTrackedAnalysis({
      api,
      taskType: 'HTP_ANALYSIS',
      title: '房树人客观观察',
      requestRef: `file:${saved.id}`,
      invoke: () => invokeGateway('htp.analyze', { fileId: saved.id, metadata, questionnaire: fields }),
      persist: ({ gateway, task }) => saveAnalysisRecord({
        moduleType: 'HTP', taskId: task.id, sourceRef: `file:${saved.id}`, title: '房树人客观观察',
        observations, features: htpFeatures(metadata, fields),
        aiSummary: extractGatewayText(gateway), ...gatewayMetadata(gateway)
      })
    });
    const { gateway, task, record } = workflow;
    const aiSummary = extractGatewayText(gateway);
    window.__mindlineContexts.htp = { fileName: file.name, story: fields.story, houseDescription: fields.houseDescription, treeDescription: fields.treeDescription, personDescription: fields.personDescription, aiSummary, taskId: task.id, recordId: record.id, time: new Date().toLocaleString() };
    const extra = aiSummary ? `<div class="card" style="margin-top:12px;padding:14px"><strong>千问辅助说明</strong><p style="margin:8px 0 0;white-space:pre-wrap">${escapeHtml(aiSummary)}</p></div>` : '';
    result.innerHTML = renderObservation('房树人客观记录', observations, gatewayNote(gateway, task, record)) + extra; toast('作品已保存并形成观察记录', 'success');
    await refreshAnalysisHistory('htp-history', 'HTP');
  } catch (error) {
    const taskNote = error.taskId ? `失败任务 ${error.taskId} 已保留，可在任务状态页查看。` : '分析任务未创建。';
    result.innerHTML = `<div class="error-box">${escapeHtml(error.message)}</div><p class="studio-result-note">${escapeHtml(taskNote)}</p>`;
    toast(error.message, 'error');
  }
  finally { setButtonBusy(button, false); }
}

async function sendAssistantMessage(message) {
  assistantState.messages.push({ role:'user', text:message }); renderAssistantMessages();
  const placeholder = { role:'assistant', text:'正在通过统一AI网关整理…', pending:true }; assistantState.messages.push(placeholder); renderAssistantMessages();
  try {
    const contexts = window.__mindlineContexts || {};
    const gateway = await invokeGateway('companion.chat', { message, history:assistantState.messages.filter(item => !item.pending).slice(-8), moduleContexts: Object.keys(contexts).length ? contexts : undefined });
    placeholder.text = extractGatewayText(gateway) || '当前真实陪伴Agent尚未配置，但统一网关已收到请求。你可以尝试描述一个具体情境、当时的感受和希望采取的小行动。';
  } catch (error) { placeholder.text = `AI网关暂不可用。先把问题缩小一点：在"${message.slice(0,40)}"这件事里，你最想先处理哪一个部分？`; }
  placeholder.pending = false; renderAssistantMessages();
}

function renderAssistantMessages() {
  const root = document.querySelector('#assistant-messages'); if (!root) return;
  root.innerHTML = assistantState.messages.map(item => `<article class="assistant-message ${item.role}${item.pending ? ' pending' : ''}"><span>${item.role === 'user' ? '你' : 'AI'}</span><p>${escapeHtml(item.text)}</p></article>`).join(''); root.scrollTop = root.scrollHeight;
}

async function saveAnalysisRecord(record) {
  return api('/analysis-records', { method:'POST', body:JSON.stringify(record) });
}

async function loadAnalysisHistory(moduleType) {
  try { return await api(`/analysis-records?moduleType=${encodeURIComponent(moduleType)}`); }
  catch { return []; }
}

function renderAnalysisHistory(records, moduleType) {
  const label = moduleType === 'SANDPLAY' ? '沙盘' : '房树人';
  const rows = Array.isArray(records) ? records.slice(0, 12) : [];
  return `<div class="studio-section-title"><div><span>历史记录</span><h2>${label}分析历史</h2></div><p>仅保存结构化观察和模型来源，可随时删除。</p></div>${rows.length ? `<div class="analysis-history-grid">${rows.map(record => `<article class="card analysis-history-card"><div class="inline"><strong>${escapeHtml(record.title)}</strong><span class="studio-pill">${escapeHtml(record.provider || (record.mockResult ? 'mock' : 'unknown'))}</span></div><small class="muted">${escapeHtml(new Date(record.createdAt).toLocaleString())} · 任务 ${escapeHtml(record.taskId)}</small><ul>${(record.observations || []).map(item => `<li>${escapeHtml(item)}</li>`).join('')}</ul>${record.aiSummary ? `<details><summary>AI 辅助摘要</summary><p>${escapeHtml(record.aiSummary)}</p></details>` : ''}<button class="btn btn-danger analysis-record-delete" data-id="${escapeHtml(record.id)}" type="button">删除记录</button></article>`).join('')}</div>` : `<div class="card section-card"><p class="muted">暂无${label}历史记录，完成一次分析后会显示在这里。</p></div>`}`;
}

function bindAnalysisHistory(rootId, moduleType) {
  const root = document.querySelector(`#${rootId}`); if (!root) return;
  root.querySelectorAll('.analysis-record-delete').forEach(button => button.addEventListener('click', async () => {
    if (!confirm('确定删除这条分析记录吗？该操作会移除结构化观察和 AI 摘要。')) return;
    setButtonBusy(button, true, '删除中…');
    try { await api(`/analysis-records/${encodeURIComponent(button.dataset.id)}`, { method:'DELETE' }); await refreshAnalysisHistory(rootId, moduleType); toast('分析记录已删除', 'success'); }
    catch (error) { toast(error.message, 'error'); setButtonBusy(button, false); }
  }));
}

async function refreshAnalysisHistory(rootId, moduleType) {
  const root = document.querySelector(`#${rootId}`); if (!root) return;
  root.innerHTML = renderAnalysisHistory(await loadAnalysisHistory(moduleType), moduleType);
  bindAnalysisHistory(rootId, moduleType);
}

function gatewayMetadata(gateway) {
  const data = gateway?.data || gateway || {};
  const mockResult = Boolean(data.mock || data.scope);
  return {
    provider: data.provider || (mockResult ? 'mock' : 'unknown'),
    model: data.model || (mockResult ? 'deterministic-mock' : 'unknown'),
    mockResult
  };
}

function sandplayFeatures(metrics) {
  return { count:metrics.count, categories:metrics.categories, quadrants:metrics.quadrants, centerRatio:metrics.centerRatio };
}

function htpFeatures(metadata, fields) {
  return {
    image:{ width:metadata.width, height:metadata.height, type:metadata.type, size:metadata.size },
    questionnaire:{
      storyLength:String(fields.story || '').length,
      houseDescriptionProvided:Boolean(String(fields.houseDescription || '').trim()),
      treeDescriptionProvided:Boolean(String(fields.treeDescription || '').trim()),
      personDescriptionProvided:Boolean(String(fields.personDescription || '').trim())
    }
  };
}
async function invokeGateway(requestedOperation, input) {
  return api('/ai/invoke', { method:'POST', headers:{'Idempotency-Key':crypto.randomUUID()}, body:JSON.stringify({ moduleCode:'MULTIMODAL_AGENT', operation:window.MINDLINE_AGENT_OPERATION || 'echo', input:{ requestedOperation, ...input }, timeoutMs:8000 }) });
}

function gatewayNote(gateway, task, record) {
  const taskNote = task?.id ? `任务 ${task.id} 已完成，可在任务状态页追踪。` : '';
const recordNote = record?.id ? `记录 ${record.id} 已持久化。` : '';
  const providerNote = gateway?.data?.mock || gateway?.data?.scope
    ? '当前连接的是基础设施 Mock，部署真实Agent后将自动替换生成说明。'
    : '已通过统一AI网关完成处理。';
  return `${providerNote}${taskNote}${recordNote}`;
}
function extractGatewayText(gateway) {
  if (gateway?.data?.mock) return '';
  return gateway?.data?.output?.reply || gateway?.data?.output?.message || gateway?.output?.reply || '';
}
function renderObservation(title, observations, note) { return `<article class="card studio-result-card"><div class="inline"><h2>${escapeHtml(title)}</h2><span class="studio-pill">非诊断性</span></div><ul>${observations.map(item => `<li>${escapeHtml(item)}</li>`).join('')}</ul><p class="studio-result-note">${note}</p></article>`; }
function setButtonBusy(button, busy, busyText) { if (!button) return; if (busy) { button.dataset.label = button.textContent; button.textContent = busyText; button.disabled = true; } else { button.textContent = button.dataset.label || button.textContent; button.disabled = false; } }
function imageMetadata(file) { return new Promise((resolve,reject) => { const image = new Image(); const url = URL.createObjectURL(file); image.onload = () => { resolve({ width:image.naturalWidth, height:image.naturalHeight, type:file.type, size:file.size }); URL.revokeObjectURL(url); }; image.onerror = () => { URL.revokeObjectURL(url); reject(new Error('无法读取图片')); }; image.src = url; }); }
function formatBytes(value) { return value < 1024 * 1024 ? `${(value / 1024).toFixed(1)} KB` : `${(value / 1024 / 1024).toFixed(1)} MB`; }
function clamp(value,min,max) { return Math.min(max, Math.max(min, value)); }
