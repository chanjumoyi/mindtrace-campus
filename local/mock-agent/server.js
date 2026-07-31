import http from 'node:http';
import { scanCrisis, SAFETY_GUIDANCE } from './crisisScanner.js';
import { sanitizeInput } from './sanitizeInput.js';

const port = Number(process.env.PORT || 8090);
const BACKEND_URL = (process.env.BACKEND_URL || 'http://backend:8080').trim();
const attemptsByRequest = new Map();

function reportRiskSignal(level, source, triggerContent) {
  const payload = JSON.stringify({ level, source, triggerContent: triggerContent.slice(0, 500) });
  fetch(`${BACKEND_URL}/api/v1/risk-signals`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: payload,
    signal: AbortSignal.timeout(3000),
  }).catch(err => console.warn(`[agent] risk signal report failed (non-blocking): ${err.message}`));
}
const MAX_BODY = 1024 * 1024;

// ── Qwen / OpenAI-compatible config ──────────────────────────────────
const LLM_MODE = (process.env.AGENT_LLM_MODE || 'qwen').trim().toLowerCase();
const QWEN_API_KEY = (process.env.QWEN_API_KEY || '').trim();
const QWEN_BASE_URL = (process.env.QWEN_BASE_URL || 'https://dashscope.aliyuncs.com/compatible-mode/v1').trim();
const QWEN_MODEL = (process.env.QWEN_MODEL || 'qwen2.5-7b-instruct').trim();
const QWEN_TIMEOUT = Number(process.env.QWEN_TIMEOUT_SECONDS || 25) * 1000;
const QWEN_MAX_ATTEMPTS = Math.max(1, Math.min(5, Number(process.env.QWEN_MAX_ATTEMPTS || 3)));

const SYSTEM_PROMPT = [
  '你是一位温和而专业的大学生心理陪伴助手，名字叫心迹。',
  '你可以做到：',
  '- 用温暖、自然的语言和用户对话，像一个耐心的朋友。',
  '- 帮助用户整理思路、梳理感受、发现自我。',
  '- 提出开放性问题，引导用户深入思考。',
  '你必须遵守以下安全边界：',
  '- 不得诊断心理疾病、人格障碍或任何医学状况。',
  '- 不得推荐药物或治疗方案。',
  '- 只能用「可能」「或许」「有些人会」等推测性表达，不能说「你有」「你患有」。',
  '- 遇到危机描述时，温和地建议联系学校心理咨询中心或拨打心理援助热线 12355。',
  '- 保持简洁温暖，每次回复控制在200字以内。',
].join('\n');

const SANDPAY_PROMPT = [
  '你是一位经验丰富的心理沙盘观察员。面对大学生来访者的沙盘作品，请你像一个温和的心理老师那样，',
  '用自然、温暖的语言描述你所看到的沙盘世界。',
  '请做到：',
  '1. 先整体描述沙盘的氛围和感觉——是丰富的还是空旷的，是活跃的还是宁静的。',
  '2. 结合元素的空间布局（象限分布、中心区域占比等），用日常语言解读这种布局可能反映的内在状态。',
  '3. 不是报数据，而是讲故事——把元素的位置、类别、密度转化为有画面感的描述。',
  '4. 最后提出2-3个开放性问题，邀请来访者自己思考沙盘的意义。',
  '5. 控制在200字以内，语气温和自然。',
  '安全边界：不得诊断、不得贴标签、不得说「意味着你…」，只能用「可能」「或许」等推测语气。',
].join('\n');

const HTP_PROMPT = [
  '你是一位资深的房树人（HTP）绘画观察员。面对大学生的绘画作品和他们的文字描述，',
  '请像一个温和的美术心理老师那样，从画面整体感受出发进行观察。',
  '请做到：',
  '1. 结合用户对房屋、树木、人物的文字描述，感受画面传达的整体情绪和氛围。',
  '2. 关注画面元素之间的关系——房子和树的位置、人物的大小和姿态、空间的使用方式。',
  '3. 用温暖的、有画面感的日常语言描述，不要列数据，不要用专业术语。',
  '4. 将用户的文字故事与画面信息融合起来，形成一个连贯的观察。',
  '5. 提出2-3个开放性问题帮助用户进一步自我探索。',
  '6. 控制在200字以内。',
  '安全边界：不得诊断、不得说画面元素「代表」「象征着」特定心理含义，只能用「可能」「或许」等推测语气。',
].join('\n');

const FORBIDDEN_PATTERNS = [
  /诊断为/, /患有/, /人格障碍/, /心理疾病/, /抑郁症/, /焦虑症/, /精神疾病/,
  /你[有患].{0,3}(抑郁|焦虑|强迫|躁狂|双相|精神分裂)/,
  /你有.{0,3}症/, /你\s*(是|有)\s*(一个|个)?\s*(抑郁|焦虑|强迫|躁郁|自闭|多动)/,
  /ni\s*you\s*(yiyuzheng|jiaolvzheng|qiangpozheng)/i,
  /ni\s*shi\s*(yiyu|jiaolv|qiangpo)/i,
];

// ── helpers ───────────────────────────────────────────────────────────

function send(res, status, body) {
  const json = JSON.stringify(body);
  res.writeHead(status, {
    'content-type': 'application/json; charset=utf-8',
    'cache-control': 'no-store',
  });
  res.end(json);
}

function readJson(req) {
  return new Promise((resolve, reject) => {
    let size = 0;
    const chunks = [];
    req.on('data', chunk => {
      size += chunk.length;
      if (size > MAX_BODY) {
        reject(new Error('BODY_TOO_LARGE'));
        req.destroy();
        return;
      }
      chunks.push(chunk);
    });
    req.on('end', () => {
      try { resolve(JSON.parse(Buffer.concat(chunks).toString('utf8') || '{}')); }
      catch { reject(new Error('INVALID_JSON')); }
    });
    req.on('error', reject);
  });
}

// ── Qwen API call ─────────────────────────────────────────────────────

async function callQwen(messages, timeoutMs) {
  const body = JSON.stringify({
    model: QWEN_MODEL,
    messages,
    temperature: 0.7,
    max_tokens: 600,
  });

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs || QWEN_TIMEOUT);

  let lastError = null;
  for (let attempt = 1; attempt <= QWEN_MAX_ATTEMPTS; attempt++) {
    try {
      const resp = await fetch(QWEN_BASE_URL.replace(/\/$/, '') + '/chat/completions', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${QWEN_API_KEY}`,
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          'User-Agent': 'MindLine-Agent/1.0',
        },
        body,
        signal: controller.signal,
      });

      if (!resp.ok) {
        const retryable = resp.status === 429 || resp.status >= 500;
        if (!retryable || attempt === QWEN_MAX_ATTEMPTS) {
          const errText = await resp.text().catch(() => '');
          throw new Error(`Qwen API HTTP ${resp.status}: ${errText.slice(0, 200)}`);
        }
        lastError = new Error(`Qwen HTTP ${resp.status} (attempt ${attempt})`);
        await sleep(350 * attempt);
        continue;
      }

      const payload = await resp.json();
      clearTimeout(timer);
      return payload.choices?.[0]?.message?.content || '';
    } catch (err) {
      clearTimeout(timer);
      if (err.name === 'AbortError') throw new Error('Qwen API timeout');
      lastError = err;
      if (attempt < QWEN_MAX_ATTEMPTS) await sleep(350 * attempt);
    }
  }
  throw lastError || new Error('Qwen retry exhausted');
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function safeContent(text) {
  const input = String(text || '');
  for (const pattern of FORBIDDEN_PATTERNS) {
    if (pattern.test(input)) return { blocked: true, reason: `响应匹配禁用语模式: ${pattern.source.slice(0, 40)}` };
  }
  return { blocked: false, text: input };
}

// ── response helpers ──────────────────────────────────────────────────

function realResponse(text, model, requestId) {
  return { status: 'SUCCEEDED', provider: 'qwen', model, output: { reply: text }, requestId };
}

function mockResponse(text, requestId) {
  return { status: 'SUCCEEDED', mock: true, provider: 'mock', model: 'deterministic-mock', output: { reply: text }, requestId };
}

// ── HTTP server ────────────────────────────────────────────────────────

const server = http.createServer(async (req, res) => {
  if (req.method === 'GET' && (req.url === '/health' || req.url === '/healthz')) {
    return send(res, 200, {
      status: 'UP',
      service: 'xinji-agent',
      llm: {
        mode: LLM_MODE,
        provider: LLM_MODE === 'mock' ? 'mock' : 'qwen',
        model: LLM_MODE === 'mock' ? 'deterministic-mock' : QWEN_MODEL,
        configured: LLM_MODE !== 'mock' && Boolean(QWEN_API_KEY),
      },
    });
  }

  if (req.method !== 'POST' || !['/v1/invoke', '/v1/chat'].includes(req.url)) {
    return send(res, 404, { code: 'NOT_FOUND', message: 'route not found' });
  }

  try {
    const body = await readJson(req);
    const requestId = String(body.requestId || 'anonymous');
    const operation = String(body.operation || '');
    const input = body.input || {};
    const count = (attemptsByRequest.get(requestId) || 0) + 1;
    attemptsByRequest.set(requestId, count);

    // ── test operations ───────────────────────────────────────────
    if (operation === 'simulate-error' && count < 3) {
      return send(res, 503, { code: 'MOCK_TRANSIENT_ERROR', message: 'temporary failure for retry verification', attempt: count });
    }
    if (operation === 'simulate-timeout') {
      const waitMs = Math.min(Number(body.timeoutMs || 1000) + 1200, 12_000);
      await new Promise(resolve => setTimeout(resolve, waitMs));
    }
    if (operation === 'health') {
      return send(res, 200, { status: 'SUCCEEDED', mock: LLM_MODE === 'mock', requestId, operation, attempt: count, output: { healthy: true } });
    }

    // ── chat / companion ──────────────────────────────────────────
    const isChatOp = operation === 'chat' || operation === 'companion.chat';
    const hasMessage = typeof input.message === 'string' && input.message.trim();
    const requestedOp = input.requestedOperation || operation || '';

    if (isChatOp || requestedOp === 'chat' ||
        (operation === 'echo' && hasMessage && (input.requestedOperation === 'companion.chat' || input.requestedOperation === 'chat'))) {

      if (LLM_MODE === 'qwen' && QWEN_API_KEY) {
        const history = Array.isArray(input.history) ? input.history : [];
        const moduleContexts = input.moduleContexts;
        let contextNote = '';
        if (moduleContexts && typeof moduleContexts === 'object') {
          const parts = [];
          if (moduleContexts.handwriting) {
            const h = moduleContexts.handwriting;
            parts.push(`【笔迹分析】参与者：${h.participantId}，任务：${h.taskType}，采样点：${h.pointCount}，书写内容：${h.writingContent || '无'}，数据质量：${h.dataQuality}，分析摘要：${h.llmSummary || '无'}`);
          }
          if (moduleContexts.sandplay) {
            const s = moduleContexts.sandplay;
            const elNames = (s.elements || []).map(e => e.label).join('、');
            parts.push(`【沙盘分析】元素(${s.elements?.length || 0}个)：${elNames}，象限分布：${JSON.stringify(s.metrics?.quadrants)}，中心占比：${s.metrics?.centerRatio}，千问分析：${s.aiSummary || '无'}`);
          }
          if (moduleContexts.htp) {
            const t = moduleContexts.htp;
            parts.push(`【房树人分析】作品：${t.fileName}，用户故事：${t.story || '无'}，房屋：${t.houseDescription || '无'}，树木：${t.treeDescription || '无'}，人物：${t.personDescription || '无'}，千问分析：${t.aiSummary || '无'}`);
          }
          if (moduleContexts.moodTrends && moduleContexts.moodTrends.points && moduleContexts.moodTrends.points.length > 0) {
            const pts = moduleContexts.moodTrends.points;
            const latest = pts[0];
            const trendDesc = pts.length >= 3
              ? `近${pts.length}天趋势：心情 ${pts[pts.length-1]?.avgMood}→${latest.avgMood}，压力 ${pts[pts.length-1]?.avgStress}→${latest.avgStress}，日均睡眠 ${latest.avgSleepHours}h`
              : `最近心情 ${latest.avgMood}/5，压力 ${latest.avgStress}/5，睡眠 ${latest.avgSleepHours}h`;
            parts.push(`【情绪趋势】${trendDesc}`);
          }
          if (parts.length) contextNote = '\n\n用户在当前会话中已完成以下模块分析，你可以在对话中自然地引用这些信息：\n' + parts.join('\n');
        }
        const fullSysPrompt = SYSTEM_PROMPT + contextNote;
        const messages = [
          { role: 'system', content: fullSysPrompt },
          ...history.filter(h => !h.pending && h.text).map(h => ({
            role: h.role === 'user' ? 'user' : 'assistant',
            content: h.text,
          })),
          { role: 'user', content: hasMessage || '你好' },
        ];

        // Crisis scan on user input (companion chat)
        const userText = hasMessage || '';
        const crisisResult = scanCrisis(userText);
        if (crisisResult.level === 'RED') {
          console.warn(`[agent] RED crisis in user input: ${crisisResult.keywords.join(', ')}`);
          reportRiskSignal('RED', 'user_input', userText);
          return send(res, 200, realResponse(SAFETY_GUIDANCE, QWEN_MODEL, requestId));
        }

        try {
          let qwenText = await callQwen(messages, Number(body.timeoutMs) || QWEN_TIMEOUT);
          // Scan AI output for safety
          const outputScan = scanCrisis(qwenText);
          if (outputScan.level === 'RED') {
            console.warn('[agent] RED crisis in AI output, replacing');
            reportRiskSignal('RED', 'ai_output', qwenText);
            qwenText = SAFETY_GUIDANCE;
          }
          const check = safeContent(qwenText);
          if (check.blocked) {
            return send(res, 200, realResponse(
              '我注意到这个话题需要更专业的支持。建议联系学校心理咨询中心，或者拨打心理援助热线 12355。',
              QWEN_MODEL, requestId));
          }
          return send(res, 200, realResponse(check.text, QWEN_MODEL, requestId));
        } catch (err) {
          console.error(`[agent] Qwen call failed: ${err.message}`);
          return send(res, 200, mockResponse(
            `千问暂时不可用（${err.message.slice(0, 80)}）。你可以先描述具体情境，我稍后可以帮你整理思路。`,
            requestId));
        }
      }

      const userMsg = hasMessage || '你好';
      return send(res, 200, mockResponse(
        `收到你的消息："${userMsg.slice(0, 60)}${userMsg.length > 60 ? '…' : ''}"。当前 Agent 未配置千问 API Key，运行在 Mock 模式下。`,
        requestId));
    }

    // ── all other operations → Qwen (sandplay, htp, handwriting, etc.) ──
    if (LLM_MODE === 'qwen' && QWEN_API_KEY) {
      try {
        const userContent = JSON.stringify(input, null, 2);
        let sysPrompt = SYSTEM_PROMPT;
        let userMsg = `请基于以下结构化数据生成温和的非诊断性观察说明（200字以内）：\n${userContent}`;
        if (requestedOp.startsWith('sandplay')) {
          sysPrompt = SANDPAY_PROMPT;
          userMsg = `请像一个心理老师那样，描述这个沙盘作品的整体感受和可能的内在状态：\n${userContent}`;
        } else if (requestedOp.startsWith('htp')) {
          sysPrompt = HTP_PROMPT;
          const imageBase64 = input.imageBase64;
          if (imageBase64 && typeof imageBase64 === 'string' && imageBase64.startsWith('data:image/')) {
            // Vision API: send the actual image to the model
            const questionnaire = input.questionnaire || {};
            const textPrompt = [
              '请像一个温和的美术心理老师那样，观察这幅房树人绘画。',
              '请做到：',
              '1. 描述画面的整体感受和情绪氛围——线条、空间使用、笔触力度给你的直观印象。',
              '2. 观察房屋、树木、人物各自的特点以及它们之间的关系。',
              '3. 结合用户的文字描述（如下），将画面信息与故事融合起来。',
              '4. 提出2-3个开放性问题帮助用户进一步自我探索。',
              '5. 控制在250字以内，语气温暖自然。',
              '',
              `绘画顺序：${questionnaire.drawingOrder || '未提供'}`,
              `画面完整度：${questionnaire.completeness || '未提供'}`,
              `用户故事：${questionnaire.story || '未提供'}`,
              `房屋描述：${questionnaire.houseDescription || '未提供'}`,
              `树木描述：${questionnaire.treeDescription || '未提供'}`,
              `人物描述：${questionnaire.personDescription || '未提供'}`,
              '',
              '安全边界：不得诊断、不得贴标签，只能用「可能」「或许」等推测语气。',
            ].join('\n');
            userMsg = textPrompt;
            userContent_forVision = [
              { type: 'image_url', image_url: { url: imageBase64 } },
              { type: 'text', text: textPrompt },
            ];
          } else {
            // Text-only fallback (no image data)
            userMsg = `请像一个温和的美术心理老师那样，描述这幅房树人绘画给人的整体感受（注意：当前无法查看图片，请仅基于元数据给出建议）：\n${userContent}`;
          }
        }
        const messages = [
          { role: 'system', content: sysPrompt },
          { role: 'user', content: (typeof userContent_forVision !== 'undefined' ? userContent_forVision : userMsg) },
        ];

        // Crisis scan on structured input (HTP/sandplay questionnaire)
        const structScan = scanCrisis(userContent);
        if (structScan.level === 'RED') {
          console.warn(`[agent] RED crisis in structured input: ${structScan.keywords.join(', ')}`);
          reportRiskSignal('RED', 'user_input', userContent.slice(0, 500));
          return send(res, 200, realResponse(SAFETY_GUIDANCE, QWEN_MODEL, requestId));
        }

        let qwenText = await callQwen(messages, Number(body.timeoutMs) || QWEN_TIMEOUT);
        // Scan AI output
        const outputScan = scanCrisis(qwenText);
        if (outputScan.level === 'RED') {
          console.warn('[agent] RED crisis in AI output, replacing');
          qwenText = SAFETY_GUIDANCE;
        }
        const check = safeContent(qwenText);
        if (check.blocked) {
          return send(res, 200, realResponse(
            '当前数据不足以形成稳定的观察。建议进一步缩小范围，聚焦具体情境。',
            QWEN_MODEL, requestId));
        }
        // Add visual observation metadata for HTP
        const isHtpOp = requestedOp.startsWith('htp');
        const responseBody = realResponse(check.text, QWEN_MODEL, requestId);
        if (isHtpOp) {
          responseBody.visualObservation = { description: check.text, model: QWEN_MODEL, analyzedAt: new Date().toISOString() };
        }
        return send(res, 200, responseBody);
      } catch (err) {
        console.error(`[agent] Qwen call failed: ${err.message}`);
        const isHtpOp = requestedOp.startsWith('htp');
        const fallback = `千问暂时不可用（${err.message.slice(0, 80)}）。本地结构化观察仍然有效。`;
        const responseBody = mockResponse(fallback, requestId);
        if (isHtpOp) {
          responseBody.visualObservation = null;
          responseBody.degradationNote = `多模态模型调用失败：${err.message.slice(0, 120)}。分析基于问卷文字描述进行。`;
          responseBody.degradationLevel = 'QUESTIONNAIRE_ONLY';
        }
        return send(res, 200, responseBody);
      }
    }

    // ── echo fallback (mock mode) ──────────────────────────────────
    return send(res, 200, {
      status: 'SUCCEEDED', mock: true,
      scope: 'timeout/retry/idempotency/logging verification only',
      requestId, moduleCode: body.moduleCode || 'COMMON', operation, attempt: count,
      output: operation === 'echo' ? body.input || {} : { healthy: true },
    });
  } catch (error) {
    return send(res, error.message === 'BODY_TOO_LARGE' ? 413 : 400, { code: error.message, message: 'invalid request' });
  }
});

server.listen(port, '0.0.0.0', () => {
  console.log(`xinji agent listening on ${port}  [llm=${LLM_MODE}${LLM_MODE === 'qwen' && QWEN_API_KEY ? ',key=***' : LLM_MODE === 'qwen' ? ',key=UNSET' : ''}]`);
});

function shutdown() {
  server.close(() => process.exit(0));
  setTimeout(() => process.exit(1), 5000).unref();
}
process.on('SIGTERM', shutdown);
process.on('SIGINT', shutdown);
