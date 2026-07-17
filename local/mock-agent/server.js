import http from 'node:http';

const port = Number(process.env.PORT || 8090);
const attemptsByRequest = new Map();
const MAX_BODY = 1024 * 1024;

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

const server = http.createServer(async (req, res) => {
  if (req.method === 'GET' && req.url === '/health') {
    return send(res, 200, { status: 'UP', service: 'xinji-mock-agent', scope: 'infrastructure-only' });
  }
  if (req.method !== 'POST' || req.url !== '/v1/invoke') {
    return send(res, 404, { code: 'NOT_FOUND', message: 'route not found' });
  }
  try {
    const body = await readJson(req);
    const requestId = String(body.requestId || 'anonymous');
    const operation = String(body.operation || '');
    const count = (attemptsByRequest.get(requestId) || 0) + 1;
    attemptsByRequest.set(requestId, count);

    if (operation === 'simulate-error' && count < 3) {
      return send(res, 503, { code: 'MOCK_TRANSIENT_ERROR', message: 'temporary failure for retry verification', attempt: count });
    }
    if (operation === 'simulate-timeout') {
      const waitMs = Math.min(Number(body.timeoutMs || 1000) + 1200, 12_000);
      await new Promise(resolve => setTimeout(resolve, waitMs));
    }
    if (!['echo', 'health', 'simulate-error', 'simulate-timeout'].includes(operation)) {
      return send(res, 422, {
        code: 'MOCK_OPERATION_UNSUPPORTED',
        message: 'Mock Agent only verifies infrastructure behavior; B owns real Agent workflows.',
        supported: ['echo', 'health', 'simulate-error', 'simulate-timeout'],
      });
    }
    return send(res, 200, {
      status: 'SUCCEEDED',
      mock: true,
      scope: 'timeout/retry/idempotency/logging verification only',
      requestId,
      moduleCode: body.moduleCode || 'COMMON',
      operation,
      attempt: count,
      output: operation === 'echo' ? body.input || {} : { healthy: true },
    });
  } catch (error) {
    return send(res, error.message === 'BODY_TOO_LARGE' ? 413 : 400, { code: error.message, message: 'invalid request' });
  }
});

server.listen(port, '0.0.0.0', () => {
  console.log(`xinji mock agent listening on ${port}`);
});

function shutdown() {
  server.close(() => process.exit(0));
  setTimeout(() => process.exit(1), 5000).unref();
}
process.on('SIGTERM', shutdown);
process.on('SIGINT', shutdown);
