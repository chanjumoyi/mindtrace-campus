import type { KwcHostAdapter } from './host-adapter.js';

export type ApiEnvelope<T> = {
  success: boolean;
  code: string;
  message: string;
  data: T;
  requestId?: string;
};

export type FoundationRequestOptions = RequestInit & {
  timeoutMs?: number;
  idempotencyKey?: string;
};

export class FoundationApiError extends Error {
  constructor(message: string, readonly code: string, readonly requestId?: string, readonly status?: number) {
    super(message);
    this.name = 'FoundationApiError';
  }
}

export class FoundationApiClient {
  private readonly normalizedBaseUrl: string;

  constructor(baseUrl: string, private readonly host: KwcHostAdapter) {
    this.normalizedBaseUrl = baseUrl.replace(/\/$/, '');
  }

  async request<T>(path: string, options: FoundationRequestOptions = {}): Promise<T> {
    const token = await this.host.getAccessToken();
    const headers = new Headers(options.headers || {});
    const requestId = createRequestId();
    if (token) headers.set('Authorization', `Bearer ${token}`);
    headers.set('X-Request-Id', requestId);
    headers.set('Accept', 'application/json');
    if (options.idempotencyKey) headers.set('Idempotency-Key', options.idempotencyKey);
    if (options.body && !(options.body instanceof FormData)) headers.set('Content-Type', 'application/json');

    const controller = new AbortController();
    const timeoutMs = Math.max(100, Math.min(options.timeoutMs ?? 10000, 120000));
    let timedOut = false;
    const timer = globalThis.setTimeout(() => {
      timedOut = true;
      controller.abort(new DOMException('Request timeout', 'TimeoutError'));
    }, timeoutMs);
    const forwardAbort = () => controller.abort(options.signal?.reason);
    if (options.signal) {
      if (options.signal.aborted) forwardAbort();
      else options.signal.addEventListener('abort', forwardAbort, { once: true });
    }
    try {
      const response = await fetch(`${this.normalizedBaseUrl}${path}`, {
        ...options,
        headers,
        signal: controller.signal
      });
      const payload = await this.readEnvelope<T>(response, requestId);
      if (!response.ok || !payload.success) {
        throw new FoundationApiError(
          `${payload.message}${payload.requestId ? ` [${payload.requestId}]` : ''}`,
          payload.code || `HTTP_${response.status}`,
          payload.requestId || requestId,
          response.status
        );
      }
      return payload.data;
    } catch (error) {
      if (error instanceof FoundationApiError) throw error;
      if (timedOut) throw new FoundationApiError('请求超时', 'CLIENT_TIMEOUT', requestId, 0);
      if (controller.signal.aborted) throw new FoundationApiError('请求已取消', 'CLIENT_ABORTED', requestId, 0);
      throw new FoundationApiError(error instanceof Error ? error.message : '网络请求失败', 'NETWORK_ERROR', requestId, 0);
    } finally {
      globalThis.clearTimeout(timer);
      options.signal?.removeEventListener('abort', forwardAbort);
    }
  }

  private async readEnvelope<T>(response: Response, requestId: string): Promise<ApiEnvelope<T>> {
    const contentType = response.headers.get('content-type') || '';
    if (!contentType.includes('application/json')) {
      return { success: false, code: `HTTP_${response.status}`, message: '服务未返回 JSON', data: undefined as T, requestId };
    }
    try {
      return await response.json() as ApiEnvelope<T>;
    } catch {
      return { success: false, code: 'INVALID_JSON', message: '服务返回 JSON 解析失败', data: undefined as T, requestId };
    }
  }
}

function createRequestId(): string {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  const random = new Uint8Array(16);
  globalThis.crypto?.getRandomValues?.(random);
  if (!random.some(value => value !== 0)) {
    for (let i = 0; i < random.length; i += 1) random[i] = Math.floor(Math.random() * 256);
  }
  random[6] = (random[6]! & 0x0f) | 0x40;
  random[8] = (random[8]! & 0x3f) | 0x80;
  const hex = Array.from(random, value => value.toString(16).padStart(2, '0')).join('');
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}
