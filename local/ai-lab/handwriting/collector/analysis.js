(() => {
  "use strict";

  const setupPanel = document.querySelector(".setup-panel");
  const formGrid = setupPanel?.querySelector(".form-grid");
  const exportActions = document.querySelector(".export-actions");
  if (!setupPanel || !formGrid || !exportActions) return;

  const anonymousId = getAnonymousId();
  const participantInput = document.querySelector("#participantId");
  const taskType = document.querySelector("#taskType");
  participantInput.value = anonymousId;
  taskType.value = "copy_text";
  window.MindLineCollectorResearchMode = false;

  const modeBox = document.createElement("div");
  modeBox.className = "analysis-mode-box";
  modeBox.innerHTML = `
    <div><strong>直接分析模式</strong><span>无需填写当前状态，系统使用匿名代号并在完成后自动分析。</span></div>
    <label><input id="researchModeToggle" type="checkbox"> 切换到研究采集模式</label>`;
  setupPanel.querySelector(".panel-title").after(modeBox);
  formGrid.classList.add("research-fields-hidden");

  const analyzeButton = document.createElement("button");
  analyzeButton.id = "analyzeOnlineButton";
  analyzeButton.className = "primary-button analyze-button";
  analyzeButton.type = "button";
  analyzeButton.textContent = "完成并分析";
  exportActions.prepend(analyzeButton);

  const result = document.createElement("section");
  result.id = "onlineAnalysisResult";
  result.className = "online-analysis-result";
  result.setAttribute("aria-live", "polite");
  exportActions.after(result);

  document.querySelector("#researchModeToggle").addEventListener("change", event => {
    window.MindLineCollectorResearchMode = event.target.checked;
    formGrid.classList.toggle("research-fields-hidden", !event.target.checked);
    if (!event.target.checked) {
      participantInput.value = anonymousId;
      taskType.value = "copy_text";
      taskType.dispatchEvent(new Event("change"));
    }
  });

  analyzeButton.addEventListener("click", async () => {
    const collector = window.MindLineCollector;
    if (!collector?.isReady?.()) {
      renderError("请先同意数据说明，并至少完成3个笔划、记录20个采样点。");
      return;
    }
    const trace = collector.buildPayload();
    analyzeButton.disabled = true;
    analyzeButton.textContent = "正在提取特征并调用大模型…";
    result.innerHTML = '<div class="analysis-loading">正在分析，请稍候…</div>';
    try {
      const response = await fetch(`${analysisBaseUrl()}/api/v1/handwriting/analyze`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({requestId: `web-${Date.now()}`, includeLlm: true, trace})
      });
      const envelope = await response.json();
      if (!response.ok || !envelope.success) throw new Error(envelope.message || `分析失败（HTTP ${response.status}）`);
      renderResult(envelope.data);
    } catch (error) {
      renderError(`${error.message}。请确认电脑上的8091分析服务已启动，移动设备与电脑处于同一网络。`);
    } finally {
      analyzeButton.disabled = false;
      analyzeButton.textContent = "完成并分析";
    }
  });

  function renderResult(data) {
    const llm = data.llmExplanation || {};
    const prediction = data.experimentalPrediction || {};
    const scores = Object.values(prediction.scores || {});
    const llmClass = llm.status === "SUCCESS" && llm.provider === "qwen" ? "success" : "warning";
    result.innerHTML = `
      <div class="analysis-heading">
        <div><span class="step">04</span><h2>分析结果</h2></div>
        <span class="model-badge ${llmClass}">${escapeHtml(llm.provider || "未调用")} / ${escapeHtml(llm.status || "无结果")}</span>
      </div>
      <div class="analysis-metrics">
        ${metric("数据质量", percent(data.dataQuality))}
        ${metric("结果置信度上限", percent(data.confidence))}
        ${metric("分析状态", data.status)}
        ${metric("模型", llm.model || "未调用")}
      </div>
      <div class="analysis-card"><h3>客观观察</h3><ul>${(data.observations || []).map(item => `<li>${escapeHtml(item.description)}</li>`).join("")}</ul></div>
      ${prediction.status === "EXPERIMENTAL" ? `<div class="analysis-card prototype-card"><h3>小样本实验性拟合</h3><div class="prototype-scores">${scores.map(item => metric(item.label, `${Number(item.value).toFixed(2)} / 5`)).join("")}</div><p>${escapeHtml(prediction.warning)}</p></div>` : `<div class="analysis-card"><h3>小样本实验性拟合</h3><p>${escapeHtml(prediction.warning || "当前未加载模型，已仅展示客观观察。")}</p></div>`}
      ${llm.summary ? `<div class="analysis-card"><h3>大模型辅助说明</h3><p>${escapeHtml(llm.summary)}</p><h4>自我探索问题</h4><ul>${(llm.explorationQuestions || []).map(item => `<li>${escapeHtml(item)}</li>`).join("")}</ul><p class="analysis-disclaimer">${escapeHtml(llm.disclaimer)}</p>${llm.degradationNote ? `<p class="analysis-warning">${escapeHtml(llm.degradationNote)}</p>` : ""}</div>` : ""}
      <div class="analysis-card"><h3>依据与限制</h3><ul>${(data.citations || []).map(item => `<li>${escapeHtml(item.sourceTitle)}，PDF第${escapeHtml(item.pdfPage)}页：${escapeHtml(item.usage)}</li>`).join("")}</ul><details><summary>查看全部限制</summary><ul>${(data.limitations || []).map(item => `<li>${escapeHtml(item)}</li>`).join("")}</ul></details></div>`;
    result.scrollIntoView({behavior: "smooth", block: "start"});
  }

  function renderError(message) {
    result.innerHTML = `<div class="analysis-error">${escapeHtml(message)}</div>`;
  }

  function analysisBaseUrl() {
    if (window.HANDWRITING_ANALYSIS_BASE_URL) return String(window.HANDWRITING_ANALYSIS_BASE_URL).replace(/\/$/, "");
    return `${window.location.protocol}//${window.location.hostname}:8091`;
  }

  function getAnonymousId() {
    const key = "mindline-anonymous-participant";
    let value = localStorage.getItem(key);
    if (!value) {
      value = `anon-${crypto.randomUUID?.() || Date.now()}`.replace(/[^a-zA-Z0-9_-]/g, "").slice(0, 40);
      localStorage.setItem(key, value);
    }
    return value;
  }

  function percent(value) {
    return value == null ? "不可用" : `${(Number(value) * 100).toFixed(1)}%`;
  }

  function metric(label, value) {
    return `<div class="analysis-metric"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`;
  }

  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, character => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"})[character]);
  }
})();
