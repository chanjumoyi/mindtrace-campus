(() => {
  "use strict";

  const FIXED_PROMPT = "请保持自然书写：今天的努力，正在成为明天的底气。";
  const FREE_PROMPT = "请用60秒自由书写：今天让我印象最深的一件事。";

  const elements = {
    canvas: document.querySelector("#writingCanvas"),
    canvasWrap: document.querySelector("#canvasWrap"),
    placeholder: document.querySelector("#canvasPlaceholder"),
    participantId: document.querySelector("#participantId"),
    taskType: document.querySelector("#taskType"),
    stressLevel: document.querySelector("#stressLevel"),
    moodLevel: document.querySelector("#moodLevel"),
    sleepQuality: document.querySelector("#sleepQuality"),
    note: document.querySelector("#note"),
    consent: document.querySelector("#consent"),
    allowNonPen: document.querySelector("#allowNonPen"),
    promptText: document.querySelector("#promptText"),
    timer: document.querySelector("#timer"),
    pointerType: document.querySelector("#pointerTypeValue"),
    pressure: document.querySelector("#pressureValue"),
    tilt: document.querySelector("#tiltValue"),
    pointCount: document.querySelector("#pointCountValue"),
    strokeCount: document.querySelector("#strokeCountValue"),
    saveStatus: document.querySelector("#saveStatus"),
    qualityBox: document.querySelector("#qualityBox"),
    newSession: document.querySelector("#newSessionButton"),
    undo: document.querySelector("#undoButton"),
    clear: document.querySelector("#clearButton"),
    replay: document.querySelector("#replayButton"),
    exportJson: document.querySelector("#exportJsonButton"),
    exportPng: document.querySelector("#exportPngButton"),
    importJson: document.querySelector("#importJsonInput")
  };

  const ctx = elements.canvas.getContext("2d", { alpha: true });
  const pointer = window.MindLinePointer;
  let state = createState();
  let activePointerId = null;
  let timerFrame = null;
  let replayFrame = null;

  function createState() {
    return {
      schemaVersion: "1.0.0",
      sessionId: self.crypto?.randomUUID?.() ?? `session-${Date.now()}`,
      createdAt: new Date().toISOString(),
      startedAt: null,
      endedAt: null,
      sessionStartEpochMs: null,
      points: [],
      strokes: [],
      currentStroke: null,
      sequence: 0,
      observedPointerTypes: new Set(),
      pressureObserved: false,
      tiltObserved: false,
      pressureValues: [],
      lastPressure: null,
      lastTiltX: null,
      lastTiltY: null,
      imported: false
    };
  }

  function resizeCanvas() {
    const rect = elements.canvasWrap.getBoundingClientRect();
    const dpr = Math.max(1, window.devicePixelRatio || 1);
    elements.canvas.width = Math.round(rect.width * dpr);
    elements.canvas.height = Math.round(rect.height * dpr);
    elements.canvas.style.width = `${rect.width}px`;
    elements.canvas.style.height = `${rect.height}px`;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    redrawAll();
  }

  function toCanvasPoint(event) {
    const rect = elements.canvas.getBoundingClientRect();
    const x = Math.min(rect.width, Math.max(0, event.clientX - rect.left));
    const y = Math.min(rect.height, Math.max(0, event.clientY - rect.top));
    return {
      x: round(x),
      y: round(y),
      xNorm: round(rect.width ? x / rect.width : 0, 6),
      yNorm: round(rect.height ? y / rect.height : 0, 6),
      canvasWidth: round(rect.width),
      canvasHeight: round(rect.height)
    };
  }

  function recordEvent(event, phase) {
    const events = typeof event.getCoalescedEvents === "function"
      ? event.getCoalescedEvents()
      : [event];

    for (const sample of events.length ? events : [event]) {
      const position = toCanvasPoint(sample);
      const pointerType = pointer.pointerType(sample, event);
      const pressureValue = pointer.pressure(sample, event);
      const pressure = pressureValue === null ? null : round(pressureValue, 4);
      const tilt = pointer.tilt(sample, event);
      const point = {
        strokeId: state.currentStroke.id,
        sequence: ++state.sequence,
        phase,
        pointerType,
        timestampEpochMs: Date.now(),
        elapsedMs: Math.max(0, Math.round(performance.now() - state.sessionStartEpochMs)),
        ...position,
        pressure,
        tiltX: pointNumber(tilt.x),
        tiltY: pointNumber(tilt.y),
        twist: pointNumber(sample.twist),
        tangentialPressure: pointerType === "pen" ? pointNumber(sample.tangentialPressure, 4) : null,
        contactWidth: pointNumber(sample.width),
        contactHeight: pointNumber(sample.height)
      };

      state.points.push(point);
      state.currentStroke.points.push(point);
      state.observedPointerTypes.add(point.pointerType);
      if (pressure !== null && pressure > 0) {
        state.lastPressure = pressure;
        state.pressureValues.push(pressure);
        if (state.pressureValues.length > 200) state.pressureValues.shift();
        const pressureRange = Math.max(...state.pressureValues) - Math.min(...state.pressureValues);
        if (pressure !== 0.5 || pressureRange >= 0.01) state.pressureObserved = true;
      }
      if (point.tiltX !== null && point.tiltY !== null) {
        state.lastTiltX = point.tiltX;
        state.lastTiltY = point.tiltY;
        if (pointerType === "pen" && (point.tiltX !== 0 || point.tiltY !== 0)) state.tiltObserved = true;
      }
      drawLatestSegment(state.currentStroke.points);
    }
    updateUi();
  }

  function startStroke(event) {
    if (!elements.consent.checked || activePointerId !== null) return;
    if (event.pointerType !== "pen" && !elements.allowNonPen.checked) return;
    event.preventDefault();
    stopReplay();
    activePointerId = event.pointerId;
    elements.canvas.setPointerCapture?.(event.pointerId);

    if (!state.startedAt) {
      state.startedAt = new Date().toISOString();
      state.sessionStartEpochMs = performance.now();
      startTimer();
    }

    const stroke = { id: state.strokes.length + 1, points: [] };
    state.currentStroke = stroke;
    state.strokes.push(stroke);
    recordEvent(event, "down");
  }

  function moveStroke(event) {
    if (event.pointerId !== activePointerId || !state.currentStroke) return;
    event.preventDefault();
    recordEvent(event, "move");
  }

  function endStroke(event) {
    if (event.pointerId !== activePointerId || !state.currentStroke) return;
    event.preventDefault();
    recordEvent(event, "up");
    state.currentStroke = null;
    state.endedAt = new Date().toISOString();
    activePointerId = null;
    updateUi();
  }

  function drawLatestSegment(points) {
    if (!points.length) return;
    const current = points[points.length - 1];
    const previous = points.length > 1 ? points[points.length - 2] : current;
    ctx.beginPath();
    ctx.moveTo(previous.x, previous.y);
    ctx.lineTo(current.x, current.y);
    ctx.strokeStyle = "#153f35";
    ctx.lineWidth = pressureToWidth(current.pressure);
    ctx.stroke();
  }

  function pressureToWidth(pressure) {
    return pressure === null ? 2.2 : Math.max(1.2, 1.2 + pressure * 3.8);
  }

  function redrawAll(pointsLimit = Infinity) {
    const rect = elements.canvas.getBoundingClientRect();
    ctx.clearRect(0, 0, rect.width, rect.height);
    let rendered = 0;
    for (const stroke of state.strokes) {
      const points = stroke.points;
      for (let i = 0; i < points.length && rendered < pointsLimit; i++, rendered++) {
        const current = points[i];
        const previous = i > 0 ? points[i - 1] : current;
        ctx.beginPath();
        ctx.moveTo(previous.x, previous.y);
        ctx.lineTo(current.x, current.y);
        ctx.strokeStyle = "#153f35";
        ctx.lineWidth = pressureToWidth(current.pressure);
        ctx.stroke();
      }
      if (rendered >= pointsLimit) break;
    }
  }

  function startTimer() {
    cancelAnimationFrame(timerFrame);
    const tick = () => {
      if (state.sessionStartEpochMs !== null) {
        const elapsed = performance.now() - state.sessionStartEpochMs;
        elements.timer.textContent = formatElapsed(elapsed);
      }
      timerFrame = requestAnimationFrame(tick);
    };
    tick();
  }

  function stopReplay() {
    if (replayFrame) cancelAnimationFrame(replayFrame);
    replayFrame = null;
  }

  function replay() {
    if (!state.points.length) return;
    stopReplay();
    let visible = 0;
    const total = state.points.length;
    const step = () => {
      visible = Math.min(total, visible + Math.max(1, Math.ceil(total / 180)));
      redrawAll(visible);
      if (visible < total) replayFrame = requestAnimationFrame(step);
      else replayFrame = null;
    };
    redrawAll(0);
    step();
  }

  function undo() {
    if (!state.strokes.length) return;
    const removed = state.strokes.pop();
    const removedIds = new Set([removed.id]);
    state.points = state.points.filter(point => !removedIds.has(point.strokeId));
    state.strokes.forEach((stroke, index) => {
      const nextId = index + 1;
      stroke.id = nextId;
      stroke.points.forEach(point => { point.strokeId = nextId; });
    });
    redrawAll();
    updateUi();
  }

  function clearDrawing() {
    stopReplay();
    state.points = [];
    state.strokes = [];
    state.currentStroke = null;
    state.sequence = 0;
    state.startedAt = null;
    state.endedAt = null;
    state.sessionStartEpochMs = null;
    state.observedPointerTypes.clear();
    state.pressureObserved = false;
    state.tiltObserved = false;
    state.pressureValues = [];
    state.lastPressure = null;
    state.lastTiltX = null;
    state.lastTiltY = null;
    cancelAnimationFrame(timerFrame);
    elements.timer.textContent = "00:00.0";
    redrawAll();
    updateUi();
  }

  function newSession() {
    stopReplay();
    cancelAnimationFrame(timerFrame);
    state = createState();
    elements.timer.textContent = "00:00.0";
    redrawAll();
    updateUi();
  }

  function buildExportPayload() {
    const rect = elements.canvas.getBoundingClientRect();
    return {
      schemaVersion: state.schemaVersion,
      sessionId: state.sessionId,
      participantId: sanitizeId(elements.participantId.value) || "self-001",
      task: {
        type: elements.taskType.value,
        promptId: elements.taskType.value === "copy_text" ? "copy-v1" : "free-v1",
        promptText: elements.promptText.textContent
      },
      consent: {
        selfDataOnly: true,
        accepted: elements.consent.checked,
        noticeVersion: "collector-notice-v1"
      },
      selfReport: {
        stressLevel: window.MindLineCollectorResearchMode ? Number(elements.stressLevel.value) : null,
        moodLevel: window.MindLineCollectorResearchMode ? Number(elements.moodLevel.value) : null,
        sleepQuality: window.MindLineCollectorResearchMode ? Number(elements.sleepQuality.value) : null,
        note: window.MindLineCollectorResearchMode ? elements.note.value.trim() : ""
      },
      device: {
        userAgent: navigator.userAgent,
        platform: navigator.platform || "unknown",
        maxTouchPoints: navigator.maxTouchPoints || 0,
        devicePixelRatio: window.devicePixelRatio || 1,
        observedPointerTypes: [...state.observedPointerTypes],
        supportsPressure: state.pressureObserved,
        supportsTilt: state.tiltObserved
      },
      canvas: {
        width: round(rect.width),
        height: round(rect.height),
        background: "ruled-paper"
      },
      timing: {
        createdAt: state.createdAt,
        startedAt: state.startedAt,
        endedAt: state.endedAt,
        durationMs: state.points.length ? state.points[state.points.length - 1].elapsedMs : 0
      },
      summary: {
        pointCount: state.points.length,
        strokeCount: state.strokes.length
      },
      points: state.points
    };
  }

  function exportJson() {
    if (!isReady()) return;
    const payload = buildExportPayload();
    downloadBlob(
      new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" }),
      `${payload.participantId}_${payload.task.promptId}_${fileTimestamp()}.json`
    );
    elements.saveStatus.textContent = "JSON已导出";
  }

  function exportPng() {
    if (!state.points.length) return;
    const exportCanvas = document.createElement("canvas");
    exportCanvas.width = elements.canvas.width;
    exportCanvas.height = elements.canvas.height;
    const exportCtx = exportCanvas.getContext("2d");
    exportCtx.fillStyle = "#fffefd";
    exportCtx.fillRect(0, 0, exportCanvas.width, exportCanvas.height);
    exportCtx.drawImage(elements.canvas, 0, 0);
    exportCanvas.toBlob(blob => {
      if (blob) downloadBlob(blob, `${sanitizeId(elements.participantId.value)}_${fileTimestamp()}.png`);
    }, "image/png");
  }

  async function importJson(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      const payload = JSON.parse(await file.text());
      if (!Array.isArray(payload.points)) throw new Error("文件缺少points数组");
      newSession();
      state.sessionId = payload.sessionId || state.sessionId;
      state.schemaVersion = payload.schemaVersion || "unknown";
      state.createdAt = payload.timing?.createdAt || state.createdAt;
      state.startedAt = payload.timing?.startedAt || null;
      state.endedAt = payload.timing?.endedAt || null;
      state.imported = true;
      elements.participantId.value = payload.participantId || "imported";
      elements.taskType.value = payload.task?.type || "copy_text";
      elements.stressLevel.value = String(payload.selfReport?.stressLevel ?? 3);
      elements.moodLevel.value = String(payload.selfReport?.moodLevel ?? 3);
      elements.sleepQuality.value = String(payload.selfReport?.sleepQuality ?? 3);
      elements.note.value = payload.selfReport?.note || "";
      elements.consent.checked = Boolean(payload.consent?.accepted);
      updatePrompt();

      const strokeMap = new Map();
      for (const rawPoint of payload.points) {
        const point = { ...rawPoint };
        if (!strokeMap.has(point.strokeId)) strokeMap.set(point.strokeId, { id: point.strokeId, points: [] });
        strokeMap.get(point.strokeId).points.push(point);
        state.points.push(point);
        state.sequence = Math.max(state.sequence, Number(point.sequence) || 0);
        state.observedPointerTypes.add(point.pointerType || "unknown");
        if (Number.isFinite(point.pressure) && point.pressure > 0) {
          state.lastPressure = point.pressure;
          state.pressureValues.push(point.pressure);
          const pressureRange = Math.max(...state.pressureValues) - Math.min(...state.pressureValues);
          if (point.pressure !== 0.5 || pressureRange >= 0.01) state.pressureObserved = true;
        }
        if (Number.isFinite(point.tiltX) && Number.isFinite(point.tiltY) && point.pointerType === "pen") {
          state.lastTiltX = point.tiltX;
          state.lastTiltY = point.tiltY;
          state.tiltObserved = true;
        }
      }
      state.strokes = [...strokeMap.values()].sort((a, b) => a.id - b.id);
      updateUi();
      replay();
      elements.saveStatus.textContent = "已导入JSON";
    } catch (error) {
      alert(`导入失败：${error.message}`);
    } finally {
      event.target.value = "";
    }
  }

  function updatePrompt() {
    elements.promptText.textContent = elements.taskType.value === "copy_text" ? FIXED_PROMPT : FREE_PROMPT;
  }

  function updateUi() {
    const hasConsent = elements.consent.checked;
    elements.placeholder.classList.toggle("hidden", hasConsent || state.points.length > 0);
    elements.canvas.style.pointerEvents = hasConsent ? "auto" : "none";
    elements.pointerType.textContent = state.observedPointerTypes.size ? [...state.observedPointerTypes].join(" / ") : "等待检测";
    elements.pressure.textContent = pressureStatus();
    elements.tilt.textContent = tiltStatus();
    elements.pointCount.textContent = String(state.points.length);
    elements.strokeCount.textContent = String(state.strokes.length);
    elements.undo.disabled = !state.strokes.length;
    elements.clear.disabled = !state.points.length;
    elements.replay.disabled = !state.points.length;
    elements.exportJson.disabled = !isReady();
    elements.exportPng.disabled = !state.points.length;

    if (isReady()) {
      elements.qualityBox.classList.add("ready");
      elements.qualityBox.innerHTML = `<strong>可以导出</strong><span>已记录 ${state.points.length} 个采样点、${state.strokes.length} 个笔划。请同时保存JSON和PNG。</span>`;
      elements.saveStatus.textContent = "数据待导出";
    } else {
      elements.qualityBox.classList.remove("ready");
      elements.qualityBox.innerHTML = `<strong>数据不足</strong><span>至少完成3个笔划、记录20个采样点后再导出。</span>`;
      elements.saveStatus.textContent = state.points.length ? "采集中" : "尚未开始";
    }
  }

  function isReady() {
    return elements.consent.checked && state.points.length >= 20 && state.strokes.length >= 3;
  }

  function pressureStatus() {
    if (state.lastPressure === null) return state.points.length ? "未检测" : "等待检测";
    const value = `${Math.round(state.lastPressure * 100)}%`;
    return state.pressureObserved ? `已检测 ${value}` : `固定值 ${value}`;
  }

  function tiltStatus() {
    if (state.lastTiltX === null || state.lastTiltY === null) return state.points.length ? "未检测" : "等待检测";
    const value = `X ${Math.round(state.lastTiltX)}° / Y ${Math.round(state.lastTiltY)}°`;
    return state.tiltObserved ? `已检测 ${value}` : `固定值 ${value}`;
  }

  function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  function formatElapsed(ms) {
    const totalTenths = Math.floor(ms / 100);
    const minutes = Math.floor(totalTenths / 600);
    const seconds = Math.floor((totalTenths % 600) / 10);
    const tenths = totalTenths % 10;
    return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}.${tenths}`;
  }

  function fileTimestamp() {
    return new Date().toISOString().replace(/[:.]/g, "-");
  }

  function sanitizeId(value) {
    return String(value || "session").trim().replace(/[^a-zA-Z0-9_-]+/g, "-").slice(0, 40);
  }

  function pointNumber(value, digits = 3) {
    return Number.isFinite(value) ? round(value, digits) : null;
  }

  function round(value, digits = 3) {
    const factor = 10 ** digits;
    return Math.round(Number(value) * factor) / factor;
  }

  elements.canvas.addEventListener("pointerdown", startStroke);
  elements.canvas.addEventListener("pointermove", moveStroke);
  elements.canvas.addEventListener("pointerup", endStroke);
  elements.canvas.addEventListener("pointercancel", endStroke);
  elements.canvas.addEventListener("contextmenu", event => event.preventDefault());
  elements.consent.addEventListener("change", updateUi);
  elements.allowNonPen.addEventListener("change", updateUi);
  elements.taskType.addEventListener("change", updatePrompt);
  elements.newSession.addEventListener("click", newSession);
  elements.undo.addEventListener("click", undo);
  elements.clear.addEventListener("click", clearDrawing);
  elements.replay.addEventListener("click", replay);
  elements.exportJson.addEventListener("click", exportJson);
  elements.exportPng.addEventListener("click", exportPng);
  elements.importJson.addEventListener("change", importJson);
  new ResizeObserver(resizeCanvas).observe(elements.canvasWrap);
  window.addEventListener("beforeunload", event => {
    if (state.points.length && elements.saveStatus.textContent !== "JSON已导出") {
      event.preventDefault();
      event.returnValue = "";
    }
  });

  window.MindLineCollector = {
    buildPayload: buildExportPayload,
    isReady
  };

  updatePrompt();
  updateUi();
  resizeCanvas();
})();
