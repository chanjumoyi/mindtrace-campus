import { api } from './api.js';
import { escapeHtml, pageHeader, toast } from './components.js';

let selectedTrace = null;

export async function handwritingPage() {
  return `<div class="content handwriting-page">
    ${pageHeader('笔迹观察', '上传华为平板采集器导出的 JSON，查看客观书写特征与 Qwen 辅助说明。')}
    <div class="scope-note"><strong>使用边界：</strong>结果只描述本次书写行为，不用于人格判断、心理评估或医学诊断。</div>
    <section class="handwriting-layout">
      <form id="handwriting-form" class="card section-card handwriting-uploader">
        <h2>1. 选择轨迹</h2>
        <div class="field"><label for="handwriting-file">采集器 JSON</label><input id="handwriting-file" type="file" accept="application/json,.json" required></div>
        <label class="check-row"><input id="handwriting-llm" type="checkbox" checked> 使用 Qwen2.5-7B 生成克制的辅助说明；未配置时自动使用 Mock</label>
        <button id="handwriting-run" class="btn btn-primary" type="submit" disabled>开始分析</button>
        <p id="handwriting-file-meta" class="muted">尚未选择文件</p>
      </form>
      <section class="card section-card handwriting-preview-card">
        <h2>2. 轨迹预览</h2>
        <canvas id="handwriting-preview" width="900" height="420" aria-label="笔迹轨迹预览"></canvas>
      </section>
    </section>
    <section id="handwriting-result" class="section" aria-live="polite"></section>
  </div>`;
}

export function bindHandwritingPage() {
  const input = document.querySelector('#handwriting-file');
  const form = document.querySelector('#handwriting-form');
  input?.addEventListener('change', async () => {
    const file = input.files?.[0];
    selectedTrace = null;
    document.querySelector('#handwriting-run').disabled = true;
    if (!file) return;
    try {
      const trace = JSON.parse(await file.text());
      if (!Array.isArray(trace.points) || !trace.points.length) throw new Error('JSON 中没有有效 points 轨迹');
      selectedTrace = trace;
      document.querySelector('#handwriting-run').disabled = false;
      document.querySelector('#handwriting-file-meta').textContent = `${trace.participantId || '匿名参与者'} · ${trace.task?.type || '未知任务'} · ${trace.points.length} 个采样点`;
      drawTrace(document.querySelector('#handwriting-preview'), trace.points);
    } catch (error) {
      document.querySelector('#handwriting-file-meta').textContent = error.message;
      toast(error.message, 'error');
    }
  });
  form?.addEventListener('submit', async event => {
    event.preventDefault();
    if (!selectedTrace) return;
    const button = document.querySelector('#handwriting-run');
    button.disabled = true; button.textContent = '分析中…';
    document.querySelector('#handwriting-result').innerHTML = '<div class="card section-card">正在提取特征并生成说明…</div>';
    try {
      const result = await api('/handwriting/analyze', {
        method: 'POST',
        body: JSON.stringify({ trace: selectedTrace, includeLlm: document.querySelector('#handwriting-llm').checked })
      });
      renderResult(result);
      toast('笔迹分析完成', 'success');
    } catch (error) {
      document.querySelector('#handwriting-result').innerHTML = `<div class="error-box">${escapeHtml(error.message)}</div>`;
      toast(error.message, 'error');
    } finally {
      button.disabled = false; button.textContent = '开始分析';
    }
  });
}

function renderResult(result) {
  const scores = result.stateScores || {};
  const pct = value => value == null ? '不可用' : `${(Number(value) * 100).toFixed(1)}%`;
  const llm = result.llmExplanation;
  const llmHtml = llm ? `<section class="card section-card">
    <div class="inline"><h2>Qwen 辅助说明</h2><span class="badge badge-${llm.status === 'SUCCESS' ? 'succeeded' : 'pending'}">${escapeHtml(llm.provider)} / ${escapeHtml(llm.status)}</span></div>
    <p>${escapeHtml(llm.summary)}</p>
    <h3>自我探索问题</h3><ul>${(llm.explorationQuestions || []).map(item => `<li>${escapeHtml(item)}</li>`).join('')}</ul>
    <p class="muted">${escapeHtml(llm.disclaimer)}</p>${llm.degradationNote ? `<div class="notice">${escapeHtml(llm.degradationNote)}</div>` : ''}
  </section>` : '';
  document.querySelector('#handwriting-result').innerHTML = `
    <div class="grid handwriting-metrics">
      ${metric('数据质量', pct(result.dataQuality))}${metric('置信度上限', pct(result.confidence))}
      ${metric('停顿指标', pct(scores.hesitation))}${metric('节律波动指标', pct(scores.rhythmInstability))}
      ${metric('设备压力指标', pct(scores.writingTension))}${metric('分析状态', result.status)}
    </div>
    <section class="card section-card"><h2>客观观察</h2><ul>${(result.observations || []).map(item => `<li><strong>${escapeHtml(item.feature)}</strong>：${escapeHtml(item.description)}</li>`).join('')}</ul></section>
    ${llmHtml}
    <section class="card section-card"><h2>依据与限制</h2><ul>${(result.citations || []).map(item => `<li>${escapeHtml(item.sourceTitle)}，PDF 第 ${escapeHtml(item.pdfPage)} 页：${escapeHtml(item.usage)}</li>`).join('')}</ul><details><summary>查看全部限制</summary><ul>${(result.limitations || []).map(item => `<li>${escapeHtml(item)}</li>`).join('')}</ul></details></section>`;
}

function metric(label, value) {
  return `<div class="card metric"><span class="muted">${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`;
}

function drawTrace(canvas, points) {
  if (!canvas) return;
  const context = canvas.getContext('2d');
  context.clearRect(0, 0, canvas.width, canvas.height);
  context.fillStyle = '#fff'; context.fillRect(0, 0, canvas.width, canvas.height);
  context.lineCap = 'round'; context.lineJoin = 'round'; context.strokeStyle = '#164e3f';
  const groups = new Map();
  points.forEach(point => { if (!groups.has(point.strokeId)) groups.set(point.strokeId, []); groups.get(point.strokeId).push(point); });
  groups.forEach(stroke => {
    if (stroke.length < 2) return;
    context.beginPath();
    stroke.forEach((point, index) => {
      const x = Number(point.xNorm) * canvas.width;
      const y = Number(point.yNorm) * canvas.height;
      context.lineWidth = Math.max(1.4, (Number(point.pressure) || .2) * 4);
      index ? context.lineTo(x, y) : context.moveTo(x, y);
    });
    context.stroke();
  });
}
