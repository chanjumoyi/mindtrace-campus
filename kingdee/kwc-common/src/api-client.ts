import type { KwcHostAdapter } from './host-adapter';

export type ApiEnvelope<T> = {
  success: boolean;
  code: string;
  message: string;
  data: T;
  requestId?: string;
};

export class FoundationApiClient {
  constructor(private readonly baseUrl: string, private readonly host: KwcHostAdapter) {}

  async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const token = await this.host.getAccessToken();
    const headers = new Headers(init.headers || {});
    if (token) headers.set('Authorization', `Bearer ${token}`);
    headers.set('X-Request-Id', crypto.randomUUID());
    if (init.body && !(init.body instanceof FormData)) headers.set('Content-Type', 'application/json');
    const response = await fetch(`${this.baseUrl}${path}`, { ...init, headers });
    const payload = await response.json() as ApiEnvelope<T>;
    if (!response.ok || !payload.success) {
      const error = new Error(`${payload.message}${payload.requestId ? ` [${payload.requestId}]` : ''}`);
      Object.assign(error, { code: payload.code, requestId: payload.requestId });
      throw error;
    }
    return payload.data;
  }
}
