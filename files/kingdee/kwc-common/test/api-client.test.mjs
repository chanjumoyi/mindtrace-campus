import test from 'node:test';
import assert from 'node:assert/strict';
import { FoundationApiClient, FoundationApiError } from '../dist/api-client.js';

const host = {
  getAccessToken: async () => 'short-lived-user-token',
  getCurrentUser: async () => ({ id: '1', username: 'demo', displayName: 'demo', roles: [], permissions: [] }),
  getLocale: () => 'zh-CN', navigate() {}, notify() {}, confirm: async () => true, emit() {}
};

test('external AbortSignal is reported as CLIENT_ABORTED instead of timeout', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async (_url, options) => {
    if (options.signal.aborted) throw options.signal.reason || new DOMException('Aborted', 'AbortError');
    return await new Promise((_resolve, reject) => options.signal.addEventListener('abort', () => reject(options.signal.reason), { once: true }));
  };
  try {
    const controller = new AbortController();
    controller.abort(new DOMException('Cancelled', 'AbortError'));
    const client = new FoundationApiClient('https://gateway.example', host);
    await assert.rejects(
      () => client.request('/api/v1/public/info', { signal: controller.signal, timeoutMs: 500 }),
      error => error instanceof FoundationApiError && error.code === 'CLIENT_ABORTED'
    );
  } finally { globalThis.fetch = originalFetch; }
});

test('request deadline is reported as CLIENT_TIMEOUT', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async (_url, options) => await new Promise((_resolve, reject) => {
    options.signal.addEventListener('abort', () => reject(options.signal.reason), { once: true });
  });
  try {
    const client = new FoundationApiClient('https://gateway.example', host);
    await assert.rejects(
      () => client.request('/api/v1/public/info', { timeoutMs: 100 }),
      error => error instanceof FoundationApiError && error.code === 'CLIENT_TIMEOUT'
    );
  } finally { globalThis.fetch = originalFetch; }
});
