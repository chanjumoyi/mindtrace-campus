import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent as ReactKeyboardEvent,
  type PointerEvent as ReactPointerEvent,
} from "react";
import { FlowStack, KeyboardInput, MobileScroll, useKeyboard, type FlowControls, type FlowScreen } from "./mobile";
import {
  ADMIN_TEST_ID,
  CHINA_PROVINCES,
  GRADE_OPTIONS,
  buildExportFilename,
  buildFollowUpParticipantId,
  createInitialParticipantId,
  formatTestNumber,
  getNextTestNumber,
  isAdministratorTestId,
  loadParticipantProfile,
  markTestCompleted,
  saveParticipantProfile,
  type ParticipantProfile,
} from "./identity";
import {
  QUESTIONNAIRE_ID,
  QUESTIONNAIRE_ITEMS,
  QUESTIONNAIRE_ITEM_SET_HASH,
  QUESTIONNAIRE_VERSION,
  RESPONSE_OPTIONS,
  calculateQuestionnaireSummary,
  formatLocalDate,
  scoreQuestionnaireAnswer,
  type QuestionnaireAnswer,
  type QuestionnaireScore,
} from "./questionnaire";
import { selectCopyPrompt, type CopyPromptAssignment } from "./writingPrompts";
import { assessWritingPattern, type WritingPatternKind } from "./writingQuality";

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
  strokeShape: { sampledStrokeCount: number; meanPathLengthPx: number; medianPathLengthPx: number; meanStraightness: number;
    meanHorizontalDisplacementRatio: number; meanAbsoluteTurnRadiansPer100Px: number };
  coverage: { widthNorm: number; heightNorm: number }; outOfBoundsPointCount: number;
};

type QualityResult = { status: "usable" | "partial" | "invalid"; canSubmit: boolean; issues: string[]; qcFlags: string[] };
type QualityMetrics = Pick<AttemptMetrics, "pointCount" | "movePointCount" | "strokeCount" | "durationMs" | "pathLengthPx" | "outOfBoundsPointCount"> &
  { strokeShape?: AttemptMetrics["strokeShape"] };

type WritingTask = {
  id: string; version: string; title: string; prompt: string; hint: string;
  quality: { minStrokes: number; minMoves: number; minDurationMs: number; minPathLength: number; requirePressure: boolean };
  copyPrompt: (CopyPromptAssignment & { repeatIndex: number; totalRepeats: number }) | null;
};

type Attempt = {
  taskId: string; taskVersion: string; taskTitle: string; prompt: string;
  copyPrompt: WritingTask["copyPrompt"];
  promptShownAt: string; startedAt: string; endedAt: string;
  canvas: { width: number; height: number; devicePixelRatio: number };
  points: Point[]; strokeCount: number; pressureDetected: boolean;
  input: { observedPointerTypes: string[]; penDetected: boolean; dynamicPressureDetected: boolean };
  interruptions: { type: string; timestamp: string; taskElapsedMs: number }[];
  metrics: AttemptMetrics; quality: QualityResult;
};

type AnswerRecord = {
  questionId: string; itemNumber: number; domain: string; domainLabel: string; question: string;
  score: QuestionnaireScore | null; rawScore: QuestionnaireScore | null; scoredScore: QuestionnaireScore | null;
  scoringDirection: "direct" | "reverse"; responseLabel: string | null; dayRange: string | null;
  missingReason: "prefer_not_to_answer" | null; shownAt: string; answeredAt: string; responseTimeMs: number;
};
type AnswerEvent = AnswerRecord & { revision: number; previousScore: QuestionnaireScore | null | "unanswered" };

type StudyState = {
  participantId: string; testNumber: number; roundId: string; assessmentId: string;
  participantProfile: ParticipantProfile | null;
  sessionStartedAt: string; consent: boolean; consentAcceptedAt: string;
  setParticipant: (profile: ParticipantProfile) => void; clearParticipant: () => void;
  setConsent: (value: boolean) => void;
  answers: QuestionnaireAnswer[]; answerRecords: (AnswerRecord | null)[]; answerEvents: AnswerEvent[];
  setAnswer: (index: number, value: QuestionnaireScore | null, shownAt: string, responseTimeMs: number) => void;
  copyPromptAssignment: CopyPromptAssignment | null; prepareWritingPlan: () => void;
  attempts: Attempt[]; addAttempt: (attempt: Attempt) => void;
};

const StudyContext = createContext<StudyState | null>(null);
const pressureTask: WritingTask = { id: "PRESS_CHECK", version: "1.1", title: "压力热身", prompt: "请用自然力度画三条横线", hint: "轻松书写即可，不需要刻意用力。", quality: { minStrokes: 3, minMoves: 24, minDurationMs: 500, minPathLength: 100, requirePressure: true }, copyPrompt: null };
const freeWritingTask: WritingTask = { id: "FREE_WRITING", version: "1.1", title: "自由书写", prompt: "请写下此刻最想记录的一件事或一种感受", hint: "建议写 20～30 个字，内容不会上传。", quality: { minStrokes: 15, minMoves: 150, minDurationMs: 4000, minPathLength: 400, requirePressure: false }, copyPrompt: null };

function createWritingTasks(assignment: CopyPromptAssignment): WritingTask[] {
  const copyTask = (repeatIndex: number): WritingTask => ({
    id: `COPY_SENTENCE_REPEAT_${repeatIndex}`,
    version: "2.0",
    title: `完整句子 · 第 ${repeatIndex} 遍`,
    prompt: `请抄写：${assignment.text}`,
    hint: repeatIndex === 1 ? "请按平时速度完整抄写，下一页会再次抄写同一句。" : "请保持平时速度，将同一句话再完整抄写一遍。",
    quality: { minStrokes: 24, minMoves: 220, minDurationMs: 5000, minPathLength: 600, requirePressure: false },
    copyPrompt: { ...assignment, repeatIndex, totalRepeats: 2 },
  });
  return [pressureTask, copyTask(1), copyTask(2), freeWritingTask];
}

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
  const strokeGroups = new Map<number, Point[]>();
  points.forEach((point) => {
    const stroke = strokeGroups.get(point.strokeId);
    if (stroke) stroke.push(point);
    else strokeGroups.set(point.strokeId, [point]);
  });
  const strokeShapes = [...strokeGroups.values()].flatMap((strokePoints) => {
    let strokePath = 0; let absoluteTurn = 0; let previousAngle: number | null = null;
    for (let index = 1; index < strokePoints.length; index += 1) {
      const dx = strokePoints[index].x - strokePoints[index - 1].x;
      const dy = strokePoints[index].y - strokePoints[index - 1].y;
      const distance = Math.hypot(dx, dy);
      strokePath += distance;
      if (distance > 0) {
        const angle = Math.atan2(dy, dx);
        if (previousAngle !== null) {
          const rawDifference = Math.abs(angle - previousAngle);
          absoluteTurn += rawDifference > Math.PI ? Math.PI * 2 - rawDifference : rawDifference;
        }
        previousAngle = angle;
      }
    }
    if (strokePath <= 0) return [];
    const first = strokePoints[0]; const last = strokePoints.at(-1) as Point;
    const displacement = Math.hypot(last.x - first.x, last.y - first.y);
    return [{ path: strokePath, straightness: displacement / strokePath,
      horizontalDisplacementRatio: Math.abs(last.x - first.x) / strokePath,
      absoluteTurnRadiansPer100Px: absoluteTurn / strokePath * 100 }];
  });
  const sortedStrokePaths = strokeShapes.map((shape) => shape.path).sort((a, b) => a - b);
  const shapeMean = (selector: (shape: (typeof strokeShapes)[number]) => number) => strokeShapes.length
    ? strokeShapes.reduce((total, shape) => total + selector(shape), 0) / strokeShapes.length : 0;
  return {
    pointCount: points.length, movePointCount: points.filter((point) => point.phase === "move").length, strokeCount,
    durationMs: round(durationMs, 1), promptToFirstContactMs: round(promptToFirstContactMs, 1), activeDurationMs: round(activeDuration, 1),
    pauseDurationMs: round(Math.max(0, durationMs - activeDuration), 1), pauseCount, pathLengthPx: round(pathLength, 1),
    averageSpeedPxPerSecond: round(activeDuration ? pathLength / activeDuration * 1000 : 0, 1), maximumSpeedPxPerSecond: round(maximumSpeed, 1),
    meanSamplingIntervalMs: round(sortedIntervals.length ? sortedIntervals.reduce((sum, value) => sum + value, 0) / sortedIntervals.length : 0, 2),
    medianSamplingIntervalMs: round(sortedIntervals.length ? sortedIntervals[Math.floor(sortedIntervals.length / 2)] : 0, 2),
    pressure: { sampleCount: pressures.length, min: round(pressureMin, 4), max: round(pressureMax, 4), mean: round(meanPressure, 4),
      standardDeviation: round(Math.sqrt(pressureVariance), 4), range: round(pressureMax - pressureMin, 4) },
    strokeShape: { sampledStrokeCount: strokeShapes.length, meanPathLengthPx: round(shapeMean((shape) => shape.path), 1),
      medianPathLengthPx: round(sortedStrokePaths.length ? sortedStrokePaths[Math.floor(sortedStrokePaths.length / 2)] : 0, 1),
      meanStraightness: round(shapeMean((shape) => shape.straightness), 4),
      meanHorizontalDisplacementRatio: round(shapeMean((shape) => shape.horizontalDisplacementRatio), 4),
      meanAbsoluteTurnRadiansPer100Px: round(shapeMean((shape) => shape.absoluteTurnRadiansPer100Px), 2) },
    coverage: { widthNorm: round(xs.length ? Math.max(...xs) - Math.min(...xs) : 0, 4), heightNorm: round(ys.length ? Math.max(...ys) - Math.min(...ys) : 0, 4) },
    outOfBoundsPointCount: points.filter((point) => !point.insideCanvas).length,
  };
}

function assessQuality(task: WritingTask, metrics: QualityMetrics, pointerType: string, pressureDetected: boolean, includePattern = true): QualityResult {
  const issues: string[] = []; const qcFlags: string[] = [];
  const addIssue = (flag: string, issue: string) => { qcFlags.push(flag); issues.push(issue); };
  if (pointerType !== "pen") addIssue("non_pen_input", "请使用数位笔书写，并确认驱动已开启 Windows Ink");
  if (metrics.strokeCount < task.quality.minStrokes) addIssue("insufficient_strokes", task.id === "PRESS_CHECK" ? "请完整画出三条横线" : "书写内容过少，请继续完成本页内容");
  if (metrics.movePointCount < task.quality.minMoves || metrics.pathLengthPx < task.quality.minPathLength) addIssue("insufficient_continuous_trajectory", "未检测到足够的连续书写轨迹");
  if (metrics.durationMs < task.quality.minDurationMs) addIssue("duration_too_short", "书写时间过短，请按平时速度完成内容");
  if (task.quality.requirePressure && !pressureDetected) addIssue("dynamic_pressure_missing", "未检测到动态笔压，请检查数位板压感设置");
  if (includePattern && metrics.strokeShape) {
    const kind: WritingPatternKind = task.id === "PRESS_CHECK" ? "pressure_check" : task.copyPrompt ? "copy_sentence" : "free_writing";
    const pattern = assessWritingPattern(kind, { strokeCount: metrics.strokeCount, durationMs: metrics.durationMs,
      meanStrokePathLengthPx: metrics.strokeShape.meanPathLengthPx, meanStrokeStraightness: metrics.strokeShape.meanStraightness,
      meanHorizontalDisplacementRatio: metrics.strokeShape.meanHorizontalDisplacementRatio,
      meanAbsoluteTurnRadiansPer100Px: metrics.strokeShape.meanAbsoluteTurnRadiansPer100Px }, task.copyPrompt?.characterCount ?? null);
    if (pattern.blocking) addIssue(pattern.qcFlags[0], kind === "pressure_check" ? "请画三条较平直的横线" : "轨迹更像连续涂画，请按题目书写完整文字");
    pattern.qcFlags.slice(1).forEach((flag) => qcFlags.push(flag));
  }
  const blockingIssues = issues.length;
  const boundaryWarning = metrics.pointCount > 0 && metrics.outOfBoundsPointCount / metrics.pointCount > 0.05;
  if (boundaryWarning) { issues.push("部分轨迹超出书写区域"); qcFlags.push("trajectory_out_of_bounds"); }
  return { status: blockingIssues ? "invalid" : boundaryWarning ? "partial" : "usable", canSubmit: blockingIssues === 0, issues, qcFlags };
}

function makeAssessmentId() {
  return globalThis.crypto?.randomUUID?.() ?? `A-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}
function makeRoundId() {
  const now = new Date();
  return `${formatLocalDate(now).replaceAll("-", "")}-${String(now.getHours()).padStart(2, "0")}${String(now.getMinutes()).padStart(2, "0")}${String(now.getSeconds()).padStart(2, "0")}`;
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
  const keyboard = useKeyboard();
  useResetScroll();
  const [mode, setMode] = useState<"initial" | "follow_up" | null>(null);
  const [age, setAge] = useState("");
  const [grade, setGrade] = useState<ParticipantProfile["grade"] | "">("");
  const [provinceCode, setProvinceCode] = useState("");
  const [prefix, setPrefix] = useState("MT");
  const [suffix, setSuffix] = useState("");
  const [identityError, setIdentityError] = useState("");

  const dismissKeyboardOutsideField = (event: ReactPointerEvent<HTMLElement>) => {
    if (!keyboard.visible || !(event.target instanceof Element)) return;
    if (event.target.closest("input, textarea")) return;
    keyboard.hide();
  };

  const dismissKeyboardOnEnter = (event: ReactKeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter") keyboard.hide();
  };

  const confirmIdentity = () => {
    setIdentityError("");
    if (mode === "initial") {
      const ageYears = Number(age);
      const province = CHINA_PROVINCES.find((entry) => entry.code === provinceCode);
      if (!Number.isInteger(ageYears) || ageYears < 10 || ageYears > 100 || !grade || !province) {
        setIdentityError("请完整填写有效年龄、年级和省份。"); return;
      }
      let participantId = createInitialParticipantId(grade);
      for (let attempt = 0; attempt < 5 && loadParticipantProfile(participantId); attempt += 1) participantId = createInitialParticipantId(grade);
      const profile: ParticipantProfile = { participantId, collectionMode: "initial", ageYears, grade,
        provinceCode: province.code, provinceLabel: province.label, profileSource: "created_on_device",
        isAdministratorTest: false, createdAt: new Date().toISOString() };
      saveParticipantProfile(profile); study.setParticipant(profile); return;
    }
    if (mode === "follow_up") {
      const participantId = buildFollowUpParticipantId(prefix, grade, suffix);
      if (!participantId || !grade) { setIdentityError("请输入两位字母、选择年级，并填写四位编号。"); return; }
      const administrator = isAdministratorTestId(participantId);
      const stored = loadParticipantProfile(participantId);
      const profile: ParticipantProfile = administrator
        ? { participantId: ADMIN_TEST_ID, collectionMode: "follow_up", ageYears: null, grade: "24", provinceCode: null,
          provinceLabel: null, profileSource: "administrator_test", isAdministratorTest: true, createdAt: null }
        : stored
          ? { ...stored, collectionMode: "follow_up", profileSource: "loaded_from_device" }
          : { participantId, collectionMode: "follow_up", ageYears: null, grade, provinceCode: null,
            provinceLabel: null, profileSource: "unavailable_on_device", isAdministratorTest: false, createdAt: null };
      study.setParticipant(profile);
    }
  };

  return <MobileScroll className="app-screen"><main className="screen-body identity-screen" onPointerDown={dismissKeyboardOutsideField}>
    <span className="step-pill">步骤 1 / 3</span><h2>参与者识别</h2>
    {!study.participantProfile ? <>
      <p className="subcopy">请选择本次属于初次测试还是后续测试。</p>
      <div className="identity-mode" role="radiogroup" aria-label="测试类型">
        <button className={mode === "initial" ? "selected" : ""} onClick={() => { setMode("initial"); setIdentityError(""); }}>初次测试</button>
        <button className={mode === "follow_up" ? "selected" : ""} onClick={() => { setMode("follow_up"); setIdentityError(""); }}>后续测试</button>
      </div>
      {mode === "initial" && <div className="identity-form">
        <label>年龄<KeyboardInput type="number" inputMode="numeric" min="10" max="100" value={age}
          onChange={(event) => setAge(event.target.value.replace(/\D/g, "").slice(0, 3))} onKeyDown={dismissKeyboardOnEnter} placeholder="请输入周岁" /></label>
        <label>年级<select value={grade} onChange={(event) => setGrade(event.target.value as ParticipantProfile["grade"] | "")}>
          <option value="">请选择</option>{GRADE_OPTIONS.map((value) => <option key={value} value={value}>{value} 级</option>)}</select></label>
        <label>来自省份<select value={provinceCode} onChange={(event) => setProvinceCode(event.target.value)}>
          <option value="">请选择</option>{CHINA_PROVINCES.map((province) => <option key={province.code} value={province.code}>{province.label}</option>)}</select></label>
      </div>}
      {mode === "follow_up" && <div className="identity-form">
        <div className="id-segments">
          <label>前两位<KeyboardInput value={prefix} maxLength={2} onChange={(event) => setPrefix(event.target.value.replace(/[^a-zA-Z]/g, "").toUpperCase())} onKeyDown={dismissKeyboardOnEnter} placeholder="MT" /></label>
          <label>年级<select value={grade} onChange={(event) => setGrade(event.target.value as ParticipantProfile["grade"] | "")}>
            <option value="">选择</option>{GRADE_OPTIONS.map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
          <label>后四位<KeyboardInput value={suffix} maxLength={4} onChange={(event) => setSuffix(event.target.value.replace(/[^a-zA-Z0-9]/g, "").toUpperCase())} onKeyDown={dismissKeyboardOnEnter} placeholder="例如 A7K9" /></label>
        </div><small className="admin-hint">管理员测试编号：{ADMIN_TEST_ID}</small>
      </div>}
      {identityError && <p className="identity-error" role="alert">{identityError}</p>}
      <button className="primary-button identity-confirm" disabled={!mode} onClick={confirmIdentity}>{mode === "initial" ? "生成采集编号" : "确认采集编号"}</button>
    </> : <>
      <div className="round-card identity-card"><span>匿名采集人 ID</span><strong>{study.participantId}</strong></div>
      <div className="round-card"><span>本次测试</span><strong>第 {study.testNumber} 次</strong><small>{formatTestNumber(study.testNumber)} · 完成保存后自动累计</small></div>
      <button className="change-identity" onClick={() => { study.clearParticipant(); setIdentityError(""); }}>重新选择测试类型</button>
      <label className="consent-row"><input type="checkbox" checked={study.consent} onChange={(event) => study.setConsent(event.target.checked)} /><span>我已了解年龄、年级、省份、问卷和书写数据的采集用途，并同意用于研究分析与模型开发并保存在本机。</span></label>
      <button className="primary-button" disabled={!study.consent} onClick={() => flow.push(questionnaireScreen)}>继续</button>
    </>}
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
        if (isLastQuestion && resolved === QUESTIONNAIRE_ITEMS.length) { study.prepareWritingPlan(); flow.push(collectionScreen); }
        else setQuestionIndex((current) => Math.min(QUESTIONNAIRE_ITEMS.length - 1, current + 1));
      }}>{isLastQuestion ? "进入书写采集" : "下一题"}</button>
    </div>
  </main></MobileScroll>;
}

function WritingPad({ task, onComplete }: { task: WritingTask; onComplete: (attempt: Attempt) => void }) {
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
  const [submissionQuality, setSubmissionQuality] = useState<QualityResult | null>(null);

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
    pressureRange.current = { min: 1, max: 0 }; setPointerType(""); setSubmissionQuality(null);
    const canvas = canvasRef.current; canvas?.getContext("2d")?.clearRect(0, 0, canvas.width, canvas.height);
  };
  const promptToFirstContactMs = points.current[0]?.taskElapsedMs ?? 0;
  const pressureDetected = penSeen.current && pressureRange.current.max - pressureRange.current.min >= 0.01;
  const liveQuality = assessQuality(task, { pointCount, movePointCount: movePointCount.current, strokeCount: strokeId.current,
    durationMs: points.current.at(-1)?.elapsedMs ?? 0, pathLengthPx: pathLength.current, outOfBoundsPointCount: outOfBoundsPointCount.current }, pointerType, pressureDetected, false);
  const finish = () => {
    const canvas = canvasRef.current;
    if (!canvas || !liveQuality.canSubmit) return;
    const rect = canvas.getBoundingClientRect();
    const metrics = calculateMetrics(points.current, promptToFirstContactMs, strokeId.current);
    const quality = assessQuality(task, metrics, pointerType, pressureDetected);
    if (!quality.canSubmit) { setSubmissionQuality(quality); return; }
    onComplete({ taskId: task.id, taskVersion: task.version, taskTitle: task.title, prompt: task.prompt, copyPrompt: task.copyPrompt,
      promptShownAt: promptShownAt.current, startedAt: startedAt.current, endedAt: new Date().toISOString(),
      canvas: { width: rect.width, height: rect.height, devicePixelRatio: window.devicePixelRatio || 1 }, points: points.current,
      strokeCount: strokeId.current, pressureDetected,
      input: { observedPointerTypes: [...observedPointerTypes.current], penDetected: penSeen.current, dynamicPressureDetected: pressureDetected },
      interruptions: interruptions.current, metrics, quality });
  };
  const displayedQuality = submissionQuality ?? liveQuality;
  const inputLabel = pointerType === "pen" ? "数位笔模式" : pointerType ? "设备处于鼠标兼容模式，请开启 Windows Ink" : "接触画布后开始书写";
  return <><div className={`device-check ${pointerType === "pen" ? "pen-ready" : pointerType ? "compat-mode" : ""}`}>
    <strong>{inputLabel}</strong>
  </div>
  <div className="canvas-wrap" data-scroll-drag="ignore"><canvas ref={canvasRef} aria-label="书写区域" data-point-count={pointCount} data-drawing={drawing.current ? "true" : "false"}
    onPointerDown={(event) => { if (!event.isPrimary || event.button !== 0) return; event.preventDefault(); setSubmissionQuality(null); observeInput(event.nativeEvent); event.currentTarget.setPointerCapture(event.pointerId); drawing.current = true; activePointerId.current = event.pointerId; strokeId.current += 1; if (!startedAt.current) { firstEventTimestamp.current = event.nativeEvent.timeStamp; startedAt.current = new Date(performance.timeOrigin + event.nativeEvent.timeStamp).toISOString(); } record(event, "down"); }}
    onPointerMove={(event) => { observeInput(event.nativeEvent); if (!drawing.current || activePointerId.current !== event.pointerId) return; if (!hasContact(event.nativeEvent)) { endStroke(event, false); return; } event.preventDefault(); record(event, "move"); }}
    onPointerUp={(event) => endStroke(event)}
    onPointerCancel={(event) => { interruptions.current.push({ type: "pointer-cancel", timestamp: new Date().toISOString(), taskElapsedMs: round(performance.now() - promptShownPerformance.current, 1) }); endStroke(event, false); }}
    onLostPointerCapture={(event) => { if (activePointerId.current === event.pointerId) { interruptions.current.push({ type: "lost-pointer-capture", timestamp: new Date().toISOString(), taskElapsedMs: round(performance.now() - promptShownPerformance.current, 1) }); drawing.current = false; activePointerId.current = null; } }} />
    {pointCount === 0 && <span className="canvas-placeholder">请在这里书写</span>}</div>
    {pointCount > 0 && <p className={`quality-hint ${displayedQuality.canSubmit ? "ready" : ""}`}>{displayedQuality.canSubmit ? "本页书写质量已达到提交要求" : displayedQuality.issues[0]}</p>}
    <div className="writing-actions" data-scroll-drag="ignore"><button type="button" className="secondary-button" onClick={clear}>清空重写</button><button type="button" className="primary-button" disabled={!liveQuality.canSubmit} onClick={finish}>确认本页书写</button></div></>;
}

function Collection({ flow }: { flow: FlowControls }) {
  const study = useStudy();
  const keyboard = useKeyboard();
  useResetScroll();
  useEffect(() => { keyboard.hide(); }, []);
  const fallbackAssignment = useMemo(() => selectCopyPrompt(), []);
  const assignment = study.copyPromptAssignment ?? fallbackAssignment;
  const tasks = useMemo(() => createWritingTasks(assignment), [assignment]);
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
    const collectionCompletedAt = study.attempts.at(-1)?.endedAt ?? exportedAt;
    const sessionId = `${study.participantId}-${formatTestNumber(study.testNumber)}-${study.assessmentId}`;
    const recallEnd = new Date(collectionCompletedAt); const recallStart = new Date(recallEnd); recallStart.setDate(recallStart.getDate() - 13);
    const answeredTimes = study.answerRecords.flatMap((record) => record ? [record.answeredAt] : []);
    const responseTimesMs = study.answerRecords.flatMap((record) => record ? [record.responseTimeMs] : []);
    const summary = calculateQuestionnaireSummary(study.answers, study.consent, responseTimesMs);
    const isAdministratorTest = study.participantProfile?.isAdministratorTest === true;
    const questionnaireQuality = isAdministratorTest ? { ...summary.quality, recordStatus: "excluded",
      qcFlags: [...summary.quality.qcFlags, "administrator_test_record"], exclusionReason: "administrator_test_record" } : summary.quality;
    const allWritingUsable = study.attempts.every((attempt) => attempt.quality.status === "usable");
    const datasetEligibility = isAdministratorTest ? "excluded_test_record"
      : questionnaireQuality.recordStatus === "usable_full" && allWritingUsable ? "eligible"
        : questionnaireQuality.recordStatus === "review_required" ? "pending_quality_review" : "partial_record";
    const payload = { schemaVersion: "1.6.0", appVersion: "handwriting-collector-mobile/1.6.0",
      sessionId, participantId: study.participantId, testNumber: study.testNumber,
      testNumberLabel: formatTestNumber(study.testNumber), roundId: study.roundId, assessmentId: study.assessmentId,
      createdAt: study.sessionStartedAt, collectionCompletedAt, exportedAt,
      dataClassification: isAdministratorTest ? "administrator_test" : "participant_collection",
      datasetEligibility,
      participant: { ...study.participantProfile, idComponents: { prefix: study.participantId.split("-")[0],
        grade: study.participantId.split("-")[1], suffix: study.participantId.split("-")[2] } },
      consent: { status: study.consent ? "granted" : "not_granted", accepted: study.consent, acceptedAt: study.consentAcceptedAt,
        version: "local-anonymous-collection-v1.2", dataUseScope: ["demographics", "research", "model_development"] },
      questionnaire: { assessmentId: study.assessmentId, testNumber: study.testNumber,
        instrumentId: QUESTIONNAIRE_ID, version: QUESTIONNAIRE_VERSION,
        responseSchemaVersion: "questionnaire-response/1.2.0", itemSetHash: QUESTIONNAIRE_ITEM_SET_HASH,
        recallPeriod: { days: 14, includesToday: true, startDate: formatLocalDate(recallStart), endDate: formatLocalDate(recallEnd),
          timezone: Intl.DateTimeFormat().resolvedOptions().timeZone },
        startedAt: study.answerRecords.find(Boolean)?.shownAt ?? study.sessionStartedAt,
        submittedAt: answeredTimes.sort().at(-1) ?? exportedAt,
        responseScale: RESPONSE_OPTIONS,
        scoring: { higherDerivedScoreMeaning: "more_reported_difficulty", rawScoreMeaning: "selected_frequency_option_0_to_4",
          reverseScoredItemIds: QUESTIONNAIRE_ITEMS.filter((item) => item.scoringDirection === "reverse").map((item) => item.id) },
        items: study.answerRecords, responseEvents: study.answerEvents,
        derived: { completionStatus: summary.completionStatus, answeredCount: summary.answeredCount,
          missingItemIds: summary.missingItemIds, domainScores: summary.domainScores, scoredItemValues: summary.scoredItemValues, symptomSumS: summary.symptomSumS,
          breadthB: summary.breadthB, frequentF: summary.frequentF, impactI: summary.impactI,
          resultTitle: summary.resultTitle, scoreRuleVersion: summary.scoreRuleVersion,
          responseTiming: summary.responseTiming },
        quality: questionnaireQuality, linkedSessionIds: [sessionId] },
      writingPlan: { copyPromptAssignment: study.copyPromptAssignment, copyRepeatsRequired: 2,
        promptSelectionIndependentOfQuestionnaire: true, selectionScope: "universal_positive_pool" },
      attempts: study.attempts.map((attempt, index) => ({ ...attempt, sessionId, testNumber: study.testNumber,
        attemptId: `${sessionId}-${attempt.taskId}-${index + 1}`, attemptNumber: index + 1 })),
      qualitySummary: { status: allWritingUsable ? "usable" : "partial",
        questionnaireRecordStatus: questionnaireQuality.recordStatus, questionnaireQcFlags: questionnaireQuality.qcFlags,
        datasetEligibility,
        usableAttempts: study.attempts.filter((attempt) => attempt.quality.status === "usable").length,
        partialAttempts: study.attempts.filter((attempt) => attempt.quality.status === "partial").length,
        invalidAttempts: study.attempts.filter((attempt) => attempt.quality.status === "invalid").length },
      device: collectDeviceContext() };
    try {
      await storePackage(payload);
      markTestCompleted(study.participantId, study.testNumber);
      const url = URL.createObjectURL(new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" }));
      const link = document.createElement("a"); link.href = url;
      link.download = buildExportFilename(study.participantId, study.testNumber, new Date(collectionCompletedAt)); link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000); setSaved(true);
    } catch {
      setSaveError("保存失败，请检查浏览器存储权限后重试。");
    } finally {
      setBusy(false);
    }
  };
  return <MobileScroll className="app-screen"><main className="screen-body review-screen">
    <div className="success-mark">✓</div><h2>本轮采集完成</h2>
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
  const [participantProfile, setParticipantProfile] = useState<ParticipantProfile | null>(null);
  const participantId = participantProfile?.participantId ?? "";
  const [testNumber, setTestNumber] = useState(0);
  const [consent, setConsentState] = useState(false); const [consentAcceptedAt, setConsentAcceptedAt] = useState("");
  const [answers, setAnswers] = useState<QuestionnaireAnswer[]>(() => Array(QUESTIONNAIRE_ITEMS.length).fill(undefined));
  const [answerRecords, setAnswerRecords] = useState<(AnswerRecord | null)[]>(() => Array(QUESTIONNAIRE_ITEMS.length).fill(null));
  const [answerEvents, setAnswerEvents] = useState<AnswerEvent[]>([]);
  const [copyPromptAssignment, setCopyPromptAssignment] = useState<CopyPromptAssignment | null>(null);
  const [attempts, setAttempts] = useState<Attempt[]>([]); const roundId = useMemo(makeRoundId, []);
  const assessmentId = useMemo(makeAssessmentId, []);
  const sessionStartedAt = useMemo(() => new Date().toISOString(), []);
  const value = useMemo<StudyState>(() => ({ participantId, testNumber, participantProfile, roundId, assessmentId, sessionStartedAt, consent, consentAcceptedAt,
    setParticipant: (profile) => { setParticipantProfile(profile); setTestNumber(getNextTestNumber(profile.participantId)); },
    clearParticipant: () => { setParticipantProfile(null); setTestNumber(0); setConsentState(false); setConsentAcceptedAt(""); setCopyPromptAssignment(null); },
    setConsent: (accepted) => { setConsentState(accepted); setConsentAcceptedAt(accepted ? new Date().toISOString() : ""); },
    answers, answerRecords, setAnswer: (index, score, shownAt, responseTimeMs) => {
      const item = QUESTIONNAIRE_ITEMS[index];
      const option = score === null ? null : RESPONSE_OPTIONS.find((entry) => entry.score === score) ?? null;
      const answeredAt = new Date().toISOString();
      const scoredScore = scoreQuestionnaireAnswer(item, score) as QuestionnaireScore | null;
      const record: AnswerRecord = { questionId: item.id, itemNumber: item.number, domain: item.domain, domainLabel: item.domainLabel,
        question: item.text, score, rawScore: score, scoredScore, scoringDirection: item.scoringDirection,
        responseLabel: option?.label ?? null, dayRange: option?.days ?? null,
        missingReason: score === null ? "prefer_not_to_answer" : null, shownAt, answeredAt, responseTimeMs: round(responseTimeMs, 1) };
      const previousScore = answers[index] === undefined ? "unanswered" : answers[index] as QuestionnaireScore | null;
      const revision = answerEvents.filter((event) => event.questionId === item.id).length + 1;
      setAnswers((current) => current.map((value, i) => i === index ? score : value));
      setAnswerRecords((current) => current.map((currentRecord, i) => i === index ? record : currentRecord));
      setAnswerEvents((current) => [...current, { ...record, revision, previousScore }]);
    }, answerEvents, copyPromptAssignment,
    prepareWritingPlan: () => setCopyPromptAssignment((current) => current ?? selectCopyPrompt()),
    attempts, addAttempt: (attempt) => setAttempts((current) => [...current, attempt]) }),
  [participantId, testNumber, participantProfile, roundId, assessmentId, sessionStartedAt, consent, consentAcceptedAt, answers, answerRecords, answerEvents, copyPromptAssignment, attempts]);
  return <StudyContext.Provider value={value}><FlowStack initial={welcomeScreen} /></StudyContext.Provider>;
}
