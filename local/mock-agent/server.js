import http from 'node:http';

const port = Number(process.env.PORT || 8090);
const attemptsByRequest = new Map();
const MAX_BODY = 1024 * 1024;

// ── Qwen / OpenAI-compatible config ──────────────────────────────────
const LLM_MODE = (process.env.AGENT_LLM_MODE || 'qwen').trim().toLowerCase();
const QWEN_API_KEY = (process.env.QWEN_API_KEY || '').trim();
const QWEN_BASE_URL = (process.env.QWEN_BASE_URL || 'https://dashscope.aliyuncs.com/compatible-mode/v1').trim();
const QWEN_MODEL = (process.env.QWEN_MODEL || 'qwen2.5-7b-instruct').trim();
const QWEN_TIMEOUT = Number(process.env.QWEN_TIMEOUT_SECONDS || 25) * 1000;
const QWEN_MAX_ATTEMPTS = Math.max(1, Math.min(5, Number(process.env.QWEN_MAX_ATTEMPTS || 3)));

const SYSTEM_PROMPT = [
  '你是心迹AI陪伴助手，为大学生提供温和的自我探索对话。',
  '你必须遵守以下安全边界：',
  '- 只能复述用户提供的情境信息，帮助用户整理思路和感受。',
  '- 不得从用户描述中推断人格、情绪障碍、心理健康状态或疾病。',
  '- 不得给出诊断、治疗建议或药物建议。',
  '- 遇到危机描述时，温和建议联系学校心理咨询中心或拨打心理援助热线。',
  '- 回答简洁温暖，控制在200字以内。',
].join('\n');

const FORBIDDEN_TERMS = ['诊断为', '患有', '人格障碍', '心理疾病', '抑郁症', '焦虑症', '精神疾病'];

// ── helpers ───────────────────────────────────────────────────────────

function send(res, status, body) {
  const json = JSON.stringify(body);
  res.writeHead(status, {
    'content-type': 'application/json; charset=utf-8',
    'content-length': Buffer.byteLength(json),
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
  for (const term of FORBIDDEN_TERMS) {
    if (String(text || '').includes(term)) return { blocked: true, reason: `响应包含禁用语: ${term}` };
  }
  return { blocked: false, text: String(text || '') };
}

// ── response helpers ──────────────────────────────────────────────────

function realResponse(text, model, requestId) {
  return { status: 'SUCCEEDED', provider: 'qwen', model, text, requestId };
}

function mockResponse(text, requestId) {
  return { status: 'SUCCEEDED', mock: true, provider: 'mock', model: 'deterministic-mock', text, requestId };
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
    const requestedOp = input.requestedOperation || '';

    if (isChatOp || requestedOp === 'companion.chat' || requestedOp === 'chat' ||
        (operation === 'echo' && hasMessage && (requestedOp === 'companion.chat' || requestedOp === 'chat'))) {

      if (LLM_MODE === 'qwen' && QWEN_API_KEY) {
        const history = Array.isArray(input.history) ? input.history : [];
        const messages = [
          { role: 'system', content: SYSTEM_PROMPT },
          ...history.filter(h => !h.pending && h.text).map(h => ({
            role: h.role === 'user' ? 'user' : 'assistant',
            content: h.text,
          })),
          { role: 'user', content: hasMessage || '你好' },
        ];

        try {
          const qwenText = await callQwen(messages, Number(body.timeoutMs) || QWEN_TIMEOUT);
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

    // ── unsupported ───────────────────────────────────────────────
    if (!['echo', 'health', 'simulate-error', 'simulate-timeout', 'chat', 'companion.chat'].includes(operation)) {
      return send(res, 422, {
        code: 'MOCK_OPERATION_UNSUPPORTED',
        message: `不支持的操作: ${operation}`,
        supported: ['echo', 'health', 'chat', 'companion.chat', 'simulate-error', 'simulate-timeout'],
      });
    }

    // ── echo fallback ─────────────────────────────────────────────
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
