import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type PointerEvent as ReactPointerEvent,
} from "react";
import { FlowStack, KeyboardInput, MobileScroll, useKeyboard, type FlowControls, type FlowScreen } from "./mobile";
import {
  QUESTIONNAIRE_ID,
  QUESTIONNAIRE_ITEMS,
  QUESTIONNAIRE_ITEM_SET_HASH,
  QUESTIONNAIRE_VERSION,
  RESPONSE_OPTIONS,
  calculateQuestionnaireSummary,
  formatLocalDate,
  type QuestionnaireAnswer,
  type QuestionnaireScore,
} from "./questionnaire";

type Point = {
  seq: number; strokeId: number; phase: "down" | "move" | "up";
  x: number; y: number; xNorm: number; yNorm: number;
  elapsedMs: number; taskElapsedMs: number; timestamp: number; eventTimestampMs: number; pressure: number;
  tangentialPressure: number; tiltX: number; tiltY: number; twist: number;
  width: number; height: number; pointerId: number; buttons: number;
  isPrimary: boolean; pointerType: string; insideCanvas: boolean; coalesced: boolean; coalescedCount: number;
};

type AttemptMetrics = {
  pointCount: number; movePointCount: number; strokeCount: number;
  durationMs: number; promptToFirstContactMs: number; activeDurationMs: number; pauseDurationMs: number;
  pauseCount: number; pathLengthPx: number; averageSpeedPxPerSecond: number; maximumSpeedPxPerSecond: number;
  meanSamplingIntervalMs: number; medianSamplingIntervalMs: number;
  pressure: { sampleCount: number; min: number; max: number; mean: number; standardDeviation: number; range: number };
  coverage: { widthNorm: number; heightNorm: number }; outOfBoundsPointCount: number;
};

type QualityResult = { status: "usable" | "partial" | "invalid"; canSubmit: boolean; issues: string[] };
type QualityMetrics = Pick<AttemptMetrics, "pointCount" | "movePointCount" | "strokeCount" | "durationMs" | "pathLengthPx" | "outOfBoundsPointCount">;

type Attempt = {
  taskId: string; taskVersion: string; taskTitle: string; prompt: string;
  promptShownAt: string; startedAt: string; endedAt: string;
  canvas: { width: number; height: number; devicePixelRatio: number };
  points: Point[]; strokeCount: number; pressureDetected: boolean;
  input: { observedPointerTypes: string[]; penDetected: boolean; dynamicPressureDetected: boolean };
  interruptions: { type: string; timestamp: string; taskElapsedMs: number }[];
  metrics: AttemptMetrics; quality: QualityResult;
};

type AnswerRecord = {
  questionId: string; itemNumber: number; domain: string; domainLabel: string; question: string;
  score: QuestionnaireScore | null; responseLabel: string | null; dayRange: string | null;
  missingReason: "prefer_not_to_answer" | null; shownAt: string; answeredAt: string; responseTimeMs: number;
};
type AnswerEvent = AnswerRecord & { revision: number; previousScore: QuestionnaireScore | null | "unanswered" };

type StudyState = {
  participantId: string; setParticipantId: (value: string) => void;
  roundId: string; assessmentId: string; sessionStartedAt: string; consent: boolean; consentAcceptedAt: string;
  setConsent: (value: boolean) => void;
  answers: QuestionnaireAnswer[]; answerRecords: (AnswerRecord | null)[]; answerEvents: AnswerEvent[];
  setAnswer: (index: number, value: QuestionnaireScore | null, shownAt: string, responseTimeMs: number) => void;
  attempts: Attempt[]; addAttempt: (attempt: Attempt) => void;
};

const StudyContext = createContext<StudyState | null>(null);
const tasks = [
  { id: "PRESS_CHECK", version: "1.1", title: "压力热身", prompt: "请用自然力度画三条横线", hint: "轻松书写即可，不需要刻意用力。", quality: { minStrokes: 3, minMoves: 24, minDurationMs: 500, minPathLength: 100, requirePressure: true } },
  { id: "COPY_SENTENCE", version: "1.1", title: "完整句子", prompt: "请抄写：今天我愿意认真感受自己的状态。", hint: "按平时写字的速度，写完整句话。", quality: { minStrokes: 20, minMoves: 180, minDurationMs: 4000, minPathLength: 500, requirePressure: false } },
  { id: "FREE_WRITING", version: "1.1", title: "自由书写", prompt: "请写下此刻最想记录的一件事或一种感受", hint: "建议写 20～30 个字，内容不会上传。", quality: { minStrokes: 15, minMoves: 150, minDurationMs: 4000, minPathLength: 400, requirePressure: false } },
];

const clamp01 = (value: number) => Math.max(0, Math.min(1, value));
const round = (value: number, digits = 3) => Number(value.toFixed(digits));

function calculateMetrics(points: Point[], promptToFirstContactMs: number, strokeCount: number): AttemptMetrics {
  let pathLength = 0; let activeDuration = 0; let maximumSpeed = 0; let pauseCount = 0;
  const intervals: number[] = []; const pressures: number[] = [];
  for (let index = 0; index < points.length; index += 1) {
    const point = points[index];
    if (point.phase !== "up" && point.pressure > 0) pressures.push(point.pressure);
    const previous = points[index - 1];
    if (!previous) continue;
    const delta = point.elapsedMs - previous.elapsedMs;
    if (delta >= 0) intervals.push(delta);
    if (point.strokeId === previous.strokeId && delta > 0) {
      const distance = Math.hypot(point.x - previous.x, point.y - previous.y);
      pathLength += distance; activeDuration += delta;
      maximumSpeed = Math.max(maximumSpeed, distance / delta * 1000);
    } else if (delta >= 500) pauseCount += 1;
  }
  const durationMs = points.at(-1)?.elapsedMs ?? 0;
  const sortedIntervals = intervals.filter((value) => value > 0).sort((a, b) => a - b);
  const meanPressure = pressures.length ? pressures.reduce((sum, value) => sum + value, 0) / pressures.length : 0;
  const pressureVariance = pressures.length ? pressures.reduce((sum, value) => sum + (value - meanPressure) ** 2, 0) / pressures.length : 0;
  const xs = points.map((point) => clamp01(point.xNorm)); const ys = points.map((point) => clamp01(point.yNorm));
  const pressureMin = pressures.length ? Math.min(...pressures) : 0; const pressureMax = pressures.length ? Math.max(...pressures) : 0;
  return {
    pointCount: points.length, movePointCount: points.filter((point) => point.phase === "move").length, strokeCount,
    durationMs: round(durationMs, 1), promptToFirstContactMs: round(promptToFirstContactMs, 1), activeDurationMs: round(activeDuration, 1),
    pauseDurationMs: round(Math.max(0, durationMs - activeDuration), 1), pauseCount, pathLengthPx: round(pathLength, 1),
    averageSpeedPxPerSecond: round(activeDuration ? pathLength / activeDuration * 1000 : 0, 1), maximumSpeedPxPerSecond: round(maximumSpeed, 1),
    meanSamplingIntervalMs: round(sortedIntervals.length ? sortedIntervals.reduce((sum, value) => sum + value, 0) / sortedIntervals.length : 0, 2),
    medianSamplingIntervalMs: round(sortedIntervals.length ? sortedIntervals[Math.floor(sortedIntervals.length / 2)] : 0, 2),
    pressure: { sampleCount: pressures.length, min: round(pressureMin, 4), max: round(pressureMax, 4), mean: round(meanPressure, 4),
      standardDeviation: round(Math.sqrt(pressureVariance), 4), range: round(pressureMax - pressureMin, 4) },
    coverage: { widthNorm: round(xs.length ? Math.max(...xs) - Math.min(...xs) : 0, 4), heightNorm: round(ys.length ? Math.max(...ys) - Math.min(...ys) : 0, 4) },
    outOfBoundsPointCount: points.filter((point) => !point.insideCanvas).length,
  };
}

function assessQuality(task: (typeof tasks)[number], metrics: QualityMetrics, pointerType: string, pressureDetected: boolean): QualityResult {
  const issues: string[] = [];
  if (pointerType !== "pen") issues.push("请使用数位笔书写，并确认驱动已开启 Windows Ink");
  if (metrics.strokeCount < task.quality.minStrokes) issues.push(task.id === "PRESS_CHECK" ? "请完整画出三条横线" : "书写内容过少，请继续完成本页内容");
  if (metrics.movePointCount < task.quality.minMoves || metrics.pathLengthPx < task.quality.minPathLength) issues.push("未检测到足够的连续书写轨迹");
  if (metrics.durationMs < task.quality.minDurationMs) issues.push("书写时间过短，请按平时速度完成内容");
  if (task.quality.requirePressure && !pressureDetected) issues.push("未检测到动态笔压，请检查数位板压感设置");
  const blockingIssues = issues.length;
  const boundaryWarning = metrics.pointCount > 0 && metrics.outOfBoundsPointCount / metrics.pointCount > 0.05;
  if (boundaryWarning) issues.push("部分轨迹超出书写区域");
  return { status: blockingIssues ? "invalid" : boundaryWarning ? "partial" : "usable", canSubmit: blockingIssues === 0, issues };
}

function makeParticipantId() { return `P${Math.random().toString(36).slice(2, 8).toUpperCase()}`; }
function makeAssessmentId() {
  return globalThis.crypto?.randomUUID?.() ?? `A-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}
function makeRoundId() {
  const now = new Date();
  return `${now.toISOString().slice(0, 10).replaceAll("-", "")}-${String(now.getHours()).padStart(2, "0")}${String(now.getMinutes()).padStart(2, "0")}`;
}
function Header({ flow, title }: { flow: FlowControls; title: string }) {
  return <div className="app-header"><button className="back-button" onClick={flow.pop} disabled={!flow.canGoBack} aria-label="返回">‹</button><span>{title}</span><span /></div>;
}
function screen(id: string, title: string, render: (flow: FlowControls) => React.ReactNode): FlowScreen {
  return { id, title, headerHeight: 54, header: (flow) => <Header flow={flow} title={title} />, render };
}
function useStudy() {
  const value = useContext(StudyContext);
  if (!value) throw new Error("Study context is unavailable");
  return value;
}
function useResetScroll() {
  useEffect(() => {
    const frame = window.requestAnimationFrame(() => {
      document.querySelector<HTMLElement>(".device-screen")?.scrollTo({ top: 0 });
      const scrolls = document.querySelectorAll<HTMLElement>(".flow-screen[data-flow-current='true'] .mobile-scroll");
      scrolls.item(scrolls.length - 1)?.scrollTo({ top: 0 });
    });
    return () => window.cancelAnimationFrame(frame);
  }, []);
}

function Welcome({ flow }: { flow: FlowControls }) {
  return <MobileScroll className="app-screen welcome-screen"><main className="welcome-content">
    <div className="brand-seal">迹</div><p className="overline">MINDTRACE · 独立采集端</p><h1>书写状态采集</h1>
    <p className="lead">完成一组简短量表、完整句子抄写与自由书写，记录笔迹、笔压、笔速和停顿。</p>
    <div className="privacy-note"><span>本机保存</span><span>匿名编号</span><span>可导出 JSON</span></div>
    <button className="primary-button" onClick={() => flow.push(identityScreen)}>开始采集</button>
    <p className="fine-print">采集结果只用于研究分析，不构成心理诊断。</p>
  </main></MobileScroll>;
}

function Identity({ flow }: { flow: FlowControls }) {
  const study = useStudy();
  useResetScroll();
  return <MobileScroll className="app-screen"><main className="screen-body">
    <span className="step-pill">步骤 1 / 3</span><h2>参与者识别</h2>
    <p className="subcopy">使用匿名编号即可，请勿填写姓名、手机号等个人信息。</p>
    <label className="field-label" htmlFor="participant">匿名参与者编号</label>
    <KeyboardInput id="participant" className="text-field" value={study.participantId} maxLength={20}
      onChange={(event) => study.setParticipantId(event.target.value.replace(/[^a-zA-Z0-9_-]/g, ""))} />
    <div className="round-card"><span>本次轮次</span><strong>{study.roundId}</strong><small>编号会根据开始时间自动生成</small></div>
    <label className="consent-row"><input type="checkbox" checked={study.consent} onChange={(event) => study.setConsent(event.target.checked)} /><span>我已了解采集内容，并同意本次匿名问卷和书写数据用于研究分析与模型开发，并保存在本机。</span></label>
    <button className="primary-button" disabled={!study.participantId.trim() || !study.consent} onClick={() => flow.push(questionnaireScreen)}>继续</button>
  </main></MobileScroll>;
}

function Questionnaire({ flow }: { flow: FlowControls }) {
  const study = useStudy();
  useResetScroll();
  const [questionIndex, setQuestionIndex] = useState(0);
  const questionShown = useRef({ index: 0, iso: new Date().toISOString(), performanceMs: performance.now() });
  useEffect(() => { questionShown.current = { index: questionIndex, iso: new Date().toISOString(), performanceMs: performance.now() }; }, [questionIndex]);
  const resolved = study.answers.filter((value) => value !== undefined).length;
  const question = QUESTIONNAIRE_ITEMS[questionIndex];
  const isLastQuestion = questionIndex === QUESTIONNAIRE_ITEMS.length - 1;
  return <MobileScroll className="app-screen"><main className="screen-body questionnaire">
    <div className="progress-row"><span>步骤 2 / 3</span><strong>{questionIndex + 1}/{QUESTIONNAIRE_ITEMS.length}</strong></div>
    <div className="progress-track"><i style={{ width: `${((questionIndex + 1) / QUESTIONNAIRE_ITEMS.length) * 100}%` }} /></div>
    <h2>过去两周的状态</h2><p className="subcopy">请按过去 14 天（包括今天）出现的天数选择。</p>
    <section className="question-card single-question" key={question.id}>
      <span className="question-domain">{question.domainLabel}</span>
      <p><b>{question.number}</b>{question.text}</p><div className="frequency-scale" role="radiogroup" aria-label={question.text}>
        {RESPONSE_OPTIONS.map((option) => <button key={option.score} className={study.answers[questionIndex] === option.score ? "selected" : ""} onClick={() => {
          const shown = questionShown.current.index === questionIndex ? questionShown.current : { iso: new Date().toISOString(), performanceMs: performance.now() };
          study.setAnswer(questionIndex, option.score, shown.iso, performance.now() - shown.performanceMs);
        }} aria-checked={study.answers[questionIndex] === option.score} role="radio"><strong>{option.label}</strong><small>{option.days}</small></button>)}
      </div>
      <button className={`skip-answer ${study.answers[questionIndex] === null ? "selected" : ""}`} onClick={() => {
        const shown = questionShown.current.index === questionIndex ? questionShown.current : { iso: new Date().toISOString(), performanceMs: performance.now() };
        study.setAnswer(questionIndex, null, shown.iso, performance.now() - shown.performanceMs);
      }}>{study.answers[questionIndex] === null ? "已选择暂不回答" : "暂不回答此题"}</button>
    </section>
    <div className={`question-nav ${questionIndex === 0 ? "single-action" : ""}`}>
      {questionIndex > 0 && <button className="secondary-button" onClick={() => setQuestionIndex((current) => current - 1)}>上一题</button>}
      <button className="primary-button" disabled={study.answers[questionIndex] === undefined} onClick={() => {
        if (isLastQuestion && resolved === QUESTIONNAIRE_ITEMS.length) flow.push(collectionScreen);
        else setQuestionIndex((current) => Math.min(QUESTIONNAIRE_ITEMS.length - 1, current + 1));
      }}>{isLastQuestion ? "进入书写采集" : "下一题"}</button>
    </div>
  </main></MobileScroll>;
}

function WritingPad({ task, onComplete }: { task: (typeof tasks)[number]; onComplete: (attempt: Attempt) => void }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const points = useRef<Point[]>([]);
  const strokeId = useRef(0);
  const startedAt = useRef("");
  const promptShownAt = useRef(new Date().toISOString());
  const promptShownPerformance = useRef(performance.now());
  const firstEventTimestamp = useRef(0);
  const drawing = useRef(false);
  const activePointerId = useRef<number | null>(null);
  const penSeen = useRef(false);
  const observedPointerTypes = useRef(new Set<string>());
  const interruptions = useRef<{ type: string; timestamp: string; taskElapsedMs: number }[]>([]);
  const pressureRange = useRef({ min: 1, max: 0 });
  const movePointCount = useRef(0);
  const pathLength = useRef(0);
  const outOfBoundsPointCount = useRef(0);
  const [pointCount, setPointCount] = useState(0);
  const [pointerType, setPointerType] = useState("");

  useEffect(() => {
    const stopDrawing = () => { drawing.current = false; activePointerId.current = null; };
    const recordVisibility = () => interruptions.current.push({ type: document.hidden ? "visibility-hidden" : "visibility-visible",
      timestamp: new Date().toISOString(), taskElapsedMs: round(performance.now() - promptShownPerformance.current, 1) });
    window.addEventListener("pointerup", stopDrawing);
    window.addEventListener("pointercancel", stopDrawing);
    document.addEventListener("visibilitychange", recordVisibility);
    return () => {
      window.removeEventListener("pointerup", stopDrawing);
      window.removeEventListener("pointercancel", stopDrawing);
      document.removeEventListener("visibilitychange", recordVisibility);
    };
  }, []);

  const hasContact = (sample: PointerEvent) =>
    sample.pointerType === "touch" || (sample.buttons & 1) === 1 || (sample.pointerType === "pen" && sample.pressure > 0);

  const observeInput = (sample: PointerEvent) => {
    if (sample.pointerType) observedPointerTypes.current.add(sample.pointerType);
    if (sample.pointerType === "pen") penSeen.current = true;
    if (sample.pointerType === "pen" && sample.pressure > 0) {
      pressureRange.current.min = Math.min(pressureRange.current.min, sample.pressure);
      pressureRange.current.max = Math.max(pressureRange.current.max, sample.pressure);
    }
    setPointerType((current) => penSeen.current ? "pen" : sample.pointerType || current);
  };

  const draw = (point: Point, previous?: Point) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const ratio = window.devicePixelRatio || 1;
    if (canvas.width !== Math.round(rect.width * ratio) || canvas.height !== Math.round(rect.height * ratio)) {
      canvas.width = Math.round(rect.width * ratio); canvas.height = Math.round(rect.height * ratio);
    }
    const context = canvas.getContext("2d");
    if (!context) return;
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    context.lineCap = "round"; context.lineJoin = "round"; context.strokeStyle = "#24332f";
    context.lineWidth = 0.7 + point.pressure * 1.8; context.beginPath();
    if (previous && previous.strokeId === point.strokeId) context.moveTo(previous.x, previous.y);
    else context.moveTo(point.x - 0.01, point.y - 0.01);
    context.lineTo(point.x, point.y); context.stroke();
  };
  const record = (event: ReactPointerEvent<HTMLCanvasElement>, phase: Point["phase"]) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const native = event.nativeEvent;
    const samples = phase === "move" && native.getCoalescedEvents ? native.getCoalescedEvents() : [native];
    samples.filter((sample) => phase !== "move" || hasContact(sample)).forEach((sample) => {
      observeInput(sample);
      const x = sample.clientX - rect.left; const y = sample.clientY - rect.top;
      const insideCanvas = x >= 0 && x <= rect.width && y >= 0 && y <= rect.height;
      const point: Point = { seq: points.current.length, strokeId: strokeId.current, phase, x, y,
        xNorm: clamp01(x / rect.width), yNorm: clamp01(y / rect.height), elapsedMs: Math.max(0, sample.timeStamp - firstEventTimestamp.current),
        taskElapsedMs: Math.max(0, sample.timeStamp - promptShownPerformance.current), timestamp: Math.round(performance.timeOrigin + sample.timeStamp),
        eventTimestampMs: sample.timeStamp, pressure: sample.pressure, tangentialPressure: sample.tangentialPressure,
        tiltX: sample.tiltX, tiltY: sample.tiltY, twist: sample.twist, width: sample.width, height: sample.height,
        pointerId: sample.pointerId, buttons: sample.buttons, isPrimary: sample.isPrimary,
        pointerType: sample.pointerType, insideCanvas, coalesced: samples.length > 1, coalescedCount: samples.length };
      const previous = points.current.at(-1);
      if (phase === "move") movePointCount.current += 1;
      if (!insideCanvas) outOfBoundsPointCount.current += 1;
      if (previous && previous.strokeId === point.strokeId) pathLength.current += Math.hypot(point.x - previous.x, point.y - previous.y);
      points.current.push(point); draw(point, previous);
    });
    setPointCount(points.current.length);
  };
  const endStroke = (event: ReactPointerEvent<HTMLCanvasElement>, recordEnd = true) => {
    if (!drawing.current || activePointerId.current !== event.pointerId) return;
    if (recordEnd) record(event, "up");
    drawing.current = false;
    activePointerId.current = null;
    try { event.currentTarget.releasePointerCapture(event.pointerId); } catch { /* capture may already be released */ }
  };
  const clear = () => {
    points.current = []; strokeId.current = 0; startedAt.current = ""; firstEventTimestamp.current = 0; setPointCount(0);
    movePointCount.current = 0; pathLength.current = 0; outOfBoundsPointCount.current = 0;
    drawing.current = false; activePointerId.current = null; penSeen.current = false; observedPointerTypes.current = new Set();
    pressureRange.current = { min: 1, max: 0 }; setPointerType("");
    const canvas = canvasRef.current; canvas?.getContext("2d")?.clearRect(0, 0, canvas.width, canvas.height);
  };
  const promptToFirstContactMs = points.current[0]?.taskElapsedMs ?? 0;
  const pressureDetected = penSeen.current && pressureRange.current.max - pressureRange.current.min >= 0.01;
  const liveQuality = assessQuality(task, { pointCount, movePointCount: movePointCount.current, strokeCount: strokeId.current,
    durationMs: points.current.at(-1)?.elapsedMs ?? 0, pathLengthPx: pathLength.current, outOfBoundsPointCount: outOfBoundsPointCount.current }, pointerType, pressureDetected);
  const finish = () => {
    const canvas = canvasRef.current;
    if (!canvas || !liveQuality.canSubmit) return;
    const rect = canvas.getBoundingClientRect();
    const metrics = calculateMetrics(points.current, promptToFirstContactMs, strokeId.current);
    const quality = assessQuality(task, metrics, pointerType, pressureDetected);
    onComplete({ taskId: task.id, taskVersion: task.version, taskTitle: task.title, prompt: task.prompt,
      promptShownAt: promptShownAt.current, startedAt: startedAt.current, endedAt: new Date().toISOString(),
      canvas: { width: rect.width, height: rect.height, devicePixelRatio: window.devicePixelRatio || 1 }, points: points.current,
      strokeCount: strokeId.current, pressureDetected,
      input: { observedPointerTypes: [...observedPointerTypes.current], penDetected: penSeen.current, dynamicPressureDetected: pressureDetected },
      interruptions: interruptions.current, metrics, quality });
  };
  const inputLabel = pointerType === "pen" ? "数位笔模式" : pointerType ? "设备处于鼠标兼容模式，请开启 Windows Ink" : "接触画布后开始书写";
  return <><div className={`device-check ${pointerType === "pen" ? "pen-ready" : pointerType ? "compat-mode" : ""}`}>
    <strong>{inputLabel}</strong>
  </div>
  <div className="canvas-wrap" data-scroll-drag="ignore"><canvas ref={canvasRef} aria-label="书写区域" data-point-count={pointCount} data-drawing={drawing.current ? "true" : "false"}
    onPointerDown={(event) => { if (!event.isPrimary || event.button !== 0) return; event.preventDefault(); observeInput(event.nativeEvent); event.currentTarget.setPointerCapture(event.pointerId); drawing.current = true; activePointerId.current = event.pointerId; strokeId.current += 1; if (!startedAt.current) { firstEventTimestamp.current = event.nativeEvent.timeStamp; startedAt.current = new Date(performance.timeOrigin + event.nativeEvent.timeStamp).toISOString(); } record(event, "down"); }}
    onPointerMove={(event) => { observeInput(event.nativeEvent); if (!drawing.current || activePointerId.current !== event.pointerId) return; if (!hasContact(event.nativeEvent)) { endStroke(event, false); return; } event.preventDefault(); record(event, "move"); }}
    onPointerUp={(event) => endStroke(event)}
    onPointerCancel={(event) => { interruptions.current.push({ type: "pointer-cancel", timestamp: new Date().toISOString(), taskElapsedMs: round(performance.now() - promptShownPerformance.current, 1) }); endStroke(event, false); }}
    onLostPointerCapture={(event) => { if (activePointerId.current === event.pointerId) { interruptions.current.push({ type: "lost-pointer-capture", timestamp: new Date().toISOString(), taskElapsedMs: round(performance.now() - promptShownPerformance.current, 1) }); drawing.current = false; activePointerId.current = null; } }} />
    {pointCount === 0 && <span className="canvas-placeholder">请在这里书写</span>}</div>
    {pointCount > 0 && <p className={`quality-hint ${liveQuality.canSubmit ? "ready" : ""}`}>{liveQuality.canSubmit ? "本页书写质量已达到提交要求" : liveQuality.issues[0]}</p>}
    <div className="writing-actions"><button className="secondary-button" onClick={clear}>清空重写</button><button className="primary-button" disabled={!liveQuality.canSubmit} onClick={finish}>确认本页书写</button></div></>;
}

function Collection({ flow }: { flow: FlowControls }) {
  const study = useStudy();
  const keyboard = useKeyboard();
  useResetScroll();
  useEffect(() => { keyboard.hide(); }, []);
  const index = study.attempts.length;
  const task = tasks[Math.min(index, tasks.length - 1)];
  return <MobileScroll className="app-screen writing-screen"><main className="screen-body">
    <div className="progress-row"><span>步骤 3 / 3</span><strong>{index + 1}/{tasks.length}</strong></div>
    <div className="progress-track"><i style={{ width: `${((index + 1) / tasks.length) * 100}%` }} /></div>
    <span className="task-tag">{task.title}</span><h2 className="prompt">{task.prompt}</h2><p className="subcopy">{task.hint}</p>
    <WritingPad key={task.id} task={task} onComplete={(attempt) => { study.addAttempt(attempt); if (index + 1 >= tasks.length) flow.replace(reviewScreen); }} />
  </main></MobileScroll>;
}

async function storePackage(payload: object) {
  await new Promise<void>((resolve, reject) => {
    const request = indexedDB.open("mindtrace-handwriting", 1);
    request.onupgradeneeded = () => request.result.createObjectStore("sessions", { keyPath: "sessionId" });
    request.onerror = () => reject(request.error);
    request.onsuccess = () => {
      const transaction = request.result.transaction("sessions", "readwrite");
      transaction.objectStore("sessions").put(payload);
      transaction.oncomplete = () => { request.result.close(); resolve(); };
      transaction.onerror = () => reject(transaction.error);
    };
  });
}

function collectDeviceContext() {
  const extendedNavigator = navigator as Navigator & { deviceMemory?: number };
  return {
    capturedAt: new Date().toISOString(), userAgent: navigator.userAgent, language: navigator.language,
    languages: navigator.languages, platform: navigator.platform, maxTouchPoints: navigator.maxTouchPoints,
    hardwareConcurrency: navigator.hardwareConcurrency, deviceMemoryGb: extendedNavigator.deviceMemory ?? null,
    online: navigator.onLine, secureContext: window.isSecureContext,
    screen: { width: window.screen.width, height: window.screen.height, availWidth: window.screen.availWidth,
      availHeight: window.screen.availHeight, colorDepth: window.screen.colorDepth, pixelDepth: window.screen.pixelDepth },
    viewport: { width: window.innerWidth, height: window.innerHeight }, devicePixelRatio: window.devicePixelRatio,
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    inputCapabilities: { coarsePointer: window.matchMedia("(pointer: coarse)").matches,
      finePointer: window.matchMedia("(pointer: fine)").matches, hover: window.matchMedia("(hover: hover)").matches },
  };
}

function Review() {
  const study = useStudy();
  useResetScroll();
  const [saved, setSaved] = useState(false); const [busy, setBusy] = useState(false); const [saveError, setSaveError] = useState("");
  const save = async () => {
    setBusy(true); setSaveError("");
    const exportedAt = new Date().toISOString();
    const sessionId = `${study.participantId}-${study.roundId}-${study.assessmentId}`;
    const recallEnd = new Date(exportedAt); const recallStart = new Date(recallEnd); recallStart.setDate(recallStart.getDate() - 13);
    const summary = calculateQuestionnaireSummary(study.answers, study.consent);
    const answeredTimes = study.answerRecords.flatMap((record) => record ? [record.answeredAt] : []);
    const payload = { schemaVersion: "1.2.0", appVersion: "handwriting-collector-mobile/1.2.0",
      sessionId, participantId: study.participantId, roundId: study.roundId, assessmentId: study.assessmentId,
      createdAt: study.sessionStartedAt, exportedAt,
      consent: { status: study.consent ? "granted" : "not_granted", accepted: study.consent, acceptedAt: study.consentAcceptedAt,
        version: "local-anonymous-collection-v1.1", dataUseScope: ["research", "model_development"] },
      questionnaire: { assessmentId: study.assessmentId, instrumentId: QUESTIONNAIRE_ID, version: QUESTIONNAIRE_VERSION,
        responseSchemaVersion: "questionnaire-response/1.1.0", itemSetHash: QUESTIONNAIRE_ITEM_SET_HASH,
        recallPeriod: { days: 14, includesToday: true, startDate: formatLocalDate(recallStart), endDate: formatLocalDate(recallEnd),
          timezone: Intl.DateTimeFormat().resolvedOptions().timeZone },
        startedAt: study.answerRecords.find(Boolean)?.shownAt ?? study.sessionStartedAt,
        submittedAt: answeredTimes.sort().at(-1) ?? exportedAt,
        responseScale: RESPONSE_OPTIONS, items: study.answerRecords, responseEvents: study.answerEvents,
        derived: { completionStatus: summary.completionStatus, answeredCount: summary.answeredCount,
          missingItemIds: summary.missingItemIds, domainScores: summary.domainScores, symptomSumS: summary.symptomSumS,
          breadthB: summary.breadthB, frequentF: summary.frequentF, impactI: summary.impactI,
          resultTitle: summary.resultTitle, scoreRuleVersion: summary.scoreRuleVersion },
        quality: summary.quality, linkedSessionIds: [sessionId] },
      attempts: study.attempts.map((attempt, index) => ({ ...attempt, sessionId,
        attemptId: `${sessionId}-${attempt.taskId}-${index + 1}`, attemptNumber: index + 1 })),
      qualitySummary: { status: study.attempts.every((attempt) => attempt.quality.status === "usable") ? "usable" : "partial",
        questionnaireRecordStatus: summary.quality.recordStatus, questionnaireQcFlags: summary.quality.qcFlags,
        usableAttempts: study.attempts.filter((attempt) => attempt.quality.status === "usable").length,
        partialAttempts: study.attempts.filter((attempt) => attempt.quality.status === "partial").length,
        invalidAttempts: study.attempts.filter((attempt) => attempt.quality.status === "invalid").length },
      device: collectDeviceContext() };
    try {
      await storePackage(payload);
      const url = URL.createObjectURL(new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" }));
      const link = document.createElement("a"); link.href = url; link.download = `${payload.sessionId}.json`; link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000); setSaved(true);
    } catch {
      setSaveError("保存失败，请检查浏览器存储权限后重试。");
    } finally {
      setBusy(false);
    }
  };
  return <MobileScroll className="app-screen"><main className="screen-body review-screen">
    <div className="success-mark">✓</div><h2>本轮采集完成</h2><p className="subcopy">请保存到本机并导出数据文件，随后可交给研究人员统一整理。</p>
    <div className="data-note"><strong>采集内容已隐藏</strong><p>采集细节仅在导出文件中完整保留，当前界面不展示任何具体数值。</p></div>
    <button className="primary-button" disabled={busy} onClick={save}>{busy ? "正在保存…" : saved ? "再次导出 JSON" : "保存并导出 JSON"}</button>
    {saved && <p className="saved-note">已保存到本机，并生成导出文件。</p>}
    {saveError && <p className="save-error" role="alert">{saveError}</p>}
  </main></MobileScroll>;
}

const identityScreen = screen("identity", "采集信息", (flow) => <Identity flow={flow} />);
const questionnaireScreen = screen("questionnaire", "状态量表", (flow) => <Questionnaire flow={flow} />);
const collectionScreen = screen("collection", "书写采集", (flow) => <Collection flow={flow} />);
const reviewScreen = screen("review", "完成采集", () => <Review />);
const welcomeScreen: FlowScreen = { id: "welcome", render: (flow) => <Welcome flow={flow} /> };

export default function Prototype() {
  const [participantId, setParticipantId] = useState(makeParticipantId);
  const [consent, setConsentState] = useState(false); const [consentAcceptedAt, setConsentAcceptedAt] = useState("");
  const [answers, setAnswers] = useState<QuestionnaireAnswer[]>(() => Array(QUESTIONNAIRE_ITEMS.length).fill(undefined));
  const [answerRecords, setAnswerRecords] = useState<(AnswerRecord | null)[]>(() => Array(QUESTIONNAIRE_ITEMS.length).fill(null));
  const [answerEvents, setAnswerEvents] = useState<AnswerEvent[]>([]);
  const [attempts, setAttempts] = useState<Attempt[]>([]); const roundId = useMemo(makeRoundId, []);
  const assessmentId = useMemo(makeAssessmentId, []);
  const sessionStartedAt = useMemo(() => new Date().toISOString(), []);
  const value = useMemo<StudyState>(() => ({ participantId, setParticipantId, roundId, assessmentId, sessionStartedAt, consent, consentAcceptedAt,
    setConsent: (accepted) => { setConsentState(accepted); setConsentAcceptedAt(accepted ? new Date().toISOString() : ""); },
    answers, answerRecords, setAnswer: (index, score, shownAt, responseTimeMs) => {
      const item = QUESTIONNAIRE_ITEMS[index];
      const option = score === null ? null : RESPONSE_OPTIONS.find((entry) => entry.score === score) ?? null;
      const answeredAt = new Date().toISOString();
      const record: AnswerRecord = { questionId: item.id, itemNumber: item.number, domain: item.domain, domainLabel: item.domainLabel,
        question: item.text, score, responseLabel: option?.label ?? null, dayRange: option?.days ?? null,
        missingReason: score === null ? "prefer_not_to_answer" : null, shownAt, answeredAt, responseTimeMs: round(responseTimeMs, 1) };
      const previousScore = answers[index] === undefined ? "unanswered" : answers[index] as QuestionnaireScore | null;
      const revision = answerEvents.filter((event) => event.questionId === item.id).length + 1;
      setAnswers((current) => current.map((value, i) => i === index ? score : value));
      setAnswerRecords((current) => current.map((currentRecord, i) => i === index ? record : currentRecord));
      setAnswerEvents((current) => [...current, { ...record, revision, previousScore }]);
    }, answerEvents, attempts, addAttempt: (attempt) => setAttempts((current) => [...current, attempt]) }),
  [participantId, roundId, assessmentId, sessionStartedAt, consent, consentAcceptedAt, answers, answerRecords, answerEvents, attempts]);
  return <StudyContext.Provider value={value}><FlowStack initial={welcomeScreen} /></StudyContext.Provider>;
}
