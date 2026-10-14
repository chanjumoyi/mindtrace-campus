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

type Point = {
  seq: number; strokeId: number; phase: "down" | "move" | "up";
  x: number; y: number; xNorm: number; yNorm: number;
  elapsedMs: number; timestamp: number; pressure: number;
  tiltX: number; tiltY: number; twist: number; width: number; height: number;
  pointerType: string; coalesced: boolean;
};

type Attempt = {
  taskId: string; prompt: string; startedAt: string; endedAt: string;
  canvas: { width: number; height: number; devicePixelRatio: number };
  points: Point[]; strokeCount: number; pressureDetected: boolean;
};

type StudyState = {
  participantId: string; setParticipantId: (value: string) => void;
  roundId: string; consent: boolean; setConsent: (value: boolean) => void;
  answers: number[]; setAnswer: (index: number, value: number) => void;
  attempts: Attempt[]; addAttempt: (attempt: Attempt) => void;
};

const StudyContext = createContext<StudyState | null>(null);
const questions = [
  "此刻，我感到平静和放松",
  "此刻，我感到有压力或紧张",
  "此刻，我能够集中注意力",
  "此刻，我感到低落或提不起精神",
];
const tasks = [
  { id: "PRESS_CHECK", title: "压力热身", prompt: "请用自然力度画三条横线", hint: "轻松书写即可，不需要刻意用力。" },
  { id: "COPY_SENTENCE", title: "完整句子", prompt: "请抄写：今天我愿意认真感受自己的状态。", hint: "按平时写字的速度，写完整句话。" },
  { id: "FREE_WRITING", title: "自由书写", prompt: "请写下此刻最想记录的一件事或一种感受", hint: "建议写 20～30 个字，内容不会上传。" },
];

function makeParticipantId() { return `P${Math.random().toString(36).slice(2, 8).toUpperCase()}`; }
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
    <label className="consent-row"><input type="checkbox" checked={study.consent} onChange={(event) => study.setConsent(event.target.checked)} /><span>我已了解采集内容，并同意在本机保存本次匿名数据。</span></label>
    <button className="primary-button" disabled={!study.participantId.trim() || !study.consent} onClick={() => flow.push(questionnaireScreen)}>继续</button>
  </main></MobileScroll>;
}

function Questionnaire({ flow }: { flow: FlowControls }) {
  const study = useStudy();
  useResetScroll();
  const answered = study.answers.filter(Boolean).length;
  return <MobileScroll className="app-screen"><main className="screen-body questionnaire">
    <div className="progress-row"><span>步骤 2 / 3</span><strong>{answered}/{questions.length}</strong></div>
    <div className="progress-track"><i style={{ width: `${(answered / questions.length) * 100}%` }} /></div>
    <h2>此刻的感受</h2><p className="subcopy">请根据现在的真实感受作答，没有正确答案。</p>
    {questions.map((question, index) => <section className="question-card" key={question}>
      <p><b>{index + 1}</b>{question}</p><div className="scale" role="radiogroup" aria-label={question}>
        {[1, 2, 3, 4, 5].map((value) => <button key={value} className={study.answers[index] === value ? "selected" : ""} onClick={() => study.setAnswer(index, value)} aria-label={`${value}分`}>{value}</button>)}
      </div><div className="scale-label"><span>完全不符合</span><span>非常符合</span></div>
    </section>)}
    <button className="primary-button" disabled={answered !== questions.length} onClick={() => flow.push(collectionScreen)}>进入书写采集</button>
  </main></MobileScroll>;
}

function WritingPad({ task, onComplete }: { task: (typeof tasks)[number]; onComplete: (attempt: Attempt) => void }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const points = useRef<Point[]>([]);
  const strokeId = useRef(0);
  const startedAt = useRef("");
  const startTime = useRef(0);
  const drawing = useRef(false);
  const [pointCount, setPointCount] = useState(0);

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
    context.lineWidth = 1.8 + point.pressure * 2.8; context.beginPath();
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
    samples.forEach((sample, sampleIndex) => {
      const x = sample.clientX - rect.left; const y = sample.clientY - rect.top;
      const point: Point = { seq: points.current.length, strokeId: strokeId.current, phase, x, y,
        xNorm: x / rect.width, yNorm: y / rect.height, elapsedMs: performance.now() - startTime.current,
        timestamp: Date.now(), pressure: sample.pressure || (sample.pointerType === "mouse" ? 0.5 : 0),
        tiltX: sample.tiltX, tiltY: sample.tiltY, twist: sample.twist, width: sample.width, height: sample.height,
        pointerType: sample.pointerType, coalesced: samples.length > 1 && sampleIndex < samples.length };
      const previous = points.current.at(-1); points.current.push(point); draw(point, previous);
    });
    setPointCount(points.current.length);
  };
  const clear = () => {
    points.current = []; strokeId.current = 0; startedAt.current = ""; setPointCount(0);
    const canvas = canvasRef.current; canvas?.getContext("2d")?.clearRect(0, 0, canvas.width, canvas.height);
  };
  const finish = () => {
    const canvas = canvasRef.current;
    if (!canvas || pointCount < 3) return;
    const rect = canvas.getBoundingClientRect();
    onComplete({ taskId: task.id, prompt: task.prompt, startedAt: startedAt.current, endedAt: new Date().toISOString(),
      canvas: { width: rect.width, height: rect.height, devicePixelRatio: window.devicePixelRatio || 1 }, points: points.current,
      strokeCount: strokeId.current, pressureDetected: points.current.some((point) => point.pressure > 0 && point.pressure !== 0.5) });
  };
  return <><div className="canvas-wrap"><canvas ref={canvasRef} aria-label="书写区域"
    onPointerDown={(event) => { event.currentTarget.setPointerCapture(event.pointerId); drawing.current = true; strokeId.current += 1; if (!startedAt.current) { startedAt.current = new Date().toISOString(); startTime.current = performance.now(); } record(event, "down"); }}
    onPointerMove={(event) => { if (drawing.current) record(event, "move"); }}
    onPointerUp={(event) => { if (drawing.current) record(event, "up"); drawing.current = false; }}
    onPointerCancel={(event) => { if (drawing.current) record(event, "up"); drawing.current = false; }} />
    {pointCount === 0 && <span className="canvas-placeholder">请在这里书写</span>}</div>
    <div className="canvas-meta"><span>{strokeId.current} 笔</span><span>{pointCount} 个采样点</span><button onClick={clear}>清空重写</button></div>
    <button className="primary-button" disabled={pointCount < 3} onClick={finish}>确认本页书写</button></>;
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

function Review() {
  const study = useStudy();
  useResetScroll();
  const [saved, setSaved] = useState(false); const [busy, setBusy] = useState(false);
  const pointTotal = study.attempts.reduce((sum, attempt) => sum + attempt.points.length, 0);
  const save = async () => {
    setBusy(true);
    const payload = { schemaVersion: "1.0.0", sessionId: `${study.participantId}-${study.roundId}`,
      participantId: study.participantId, roundId: study.roundId, createdAt: new Date().toISOString(),
      questionnaire: questions.map((question, index) => ({ question, score: study.answers[index] })), attempts: study.attempts,
      device: { userAgent: navigator.userAgent, language: navigator.language, platform: navigator.platform,
        screen: { width: window.screen.width, height: window.screen.height }, devicePixelRatio: window.devicePixelRatio } };
    await storePackage(payload);
    const url = URL.createObjectURL(new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" }));
    const link = document.createElement("a"); link.href = url; link.download = `${payload.sessionId}.json`; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000); setBusy(false); setSaved(true);
  };
  return <MobileScroll className="app-screen"><main className="screen-body review-screen">
    <div className="success-mark">✓</div><h2>本轮采集完成</h2><p className="subcopy">请保存到本机并导出数据文件，随后可交给研究人员统一整理。</p>
    <div className="summary-grid"><div><strong>{tasks.length}</strong><span>书写任务</span></div><div><strong>{pointTotal}</strong><span>轨迹点</span></div><div><strong>{study.answers.length}</strong><span>量表题目</span></div><div><strong>{study.attempts.filter((a) => a.pressureDetected).length}</strong><span>有压感任务</span></div></div>
    <div className="data-note"><strong>数据包含</strong><p>匿名编号、量表答案、完整句子与自由书写轨迹、时间、压力、倾角、笔画和设备信息。</p></div>
    <button className="primary-button" disabled={busy} onClick={save}>{busy ? "正在保存…" : saved ? "再次导出 JSON" : "保存并导出 JSON"}</button>
    {saved && <p className="saved-note">已保存到本机，并生成导出文件。</p>}
  </main></MobileScroll>;
}

const identityScreen = screen("identity", "采集信息", (flow) => <Identity flow={flow} />);
const questionnaireScreen = screen("questionnaire", "状态量表", (flow) => <Questionnaire flow={flow} />);
const collectionScreen = screen("collection", "书写采集", (flow) => <Collection flow={flow} />);
const reviewScreen = screen("review", "完成采集", () => <Review />);
const welcomeScreen: FlowScreen = { id: "welcome", render: (flow) => <Welcome flow={flow} /> };

export default function Prototype() {
  const [participantId, setParticipantId] = useState(makeParticipantId);
  const [consent, setConsent] = useState(false); const [answers, setAnswers] = useState([0, 0, 0, 0]);
  const [attempts, setAttempts] = useState<Attempt[]>([]); const roundId = useMemo(makeRoundId, []);
  const value = useMemo<StudyState>(() => ({ participantId, setParticipantId, roundId, consent, setConsent, answers,
    setAnswer: (index, score) => setAnswers((current) => current.map((value, i) => i === index ? score : value)),
    attempts, addAttempt: (attempt) => setAttempts((current) => [...current, attempt]) }), [participantId, roundId, consent, answers, attempts]);
  return <StudyContext.Provider value={value}><FlowStack initial={welcomeScreen} /></StudyContext.Provider>;
}
