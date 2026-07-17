const API_PREFIX = window.XINJI_API_PREFIX || '/api/v1';

export const session = {
  get token() { return sessionStorage.getItem('xinji_token') || ''; },
  set token(value) { value ? sessionStorage.setItem('xinji_token', value) : sessionStorage.removeItem('xinji_token'); },
  get user() { try { return JSON.parse(sessionStorage.getItem('xinji_user') || 'null'); } catch { return null; } },
  set user(value) { value ? sessionStorage.setItem('xinji_user', JSON.stringify(value)) : sessionStorage.removeItem('xinji_user'); },
  clear() { this.token = ''; this.user = null; }
};

export async function api(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (!(options.body instanceof FormData) && options.body !== undefined) headers.set('Content-Type', 'application/json');
  if (session.token) headers.set('Authorization', `Bearer ${session.token}`);
  headers.set('X-Request-Id', crypto.randomUUID());
  const response = await fetch(`${API_PREFIX}${path}`, { ...options, headers });
  const contentType = response.headers.get('content-type') || '';
  const payload = contentType.includes('application/json') ? await response.json() : null;
  if (!response.ok || (payload && payload.success === false)) {
    if (response.status === 401) session.clear();
    const error = new Error(payload?.message || `请求失败 (${response.status})`);
    error.code = payload?.code || `HTTP_${response.status}`;
    error.requestId = payload?.requestId || response.headers.get('x-request-id');
    throw error;
  }
  return payload?.data ?? payload;
}

export async function downloadFile(id, filename) {
  const response = await fetch(`${API_PREFIX}/files/${encodeURIComponent(id)}/content`, {
    headers: { Authorization: `Bearer ${session.token}`, 'X-Request-Id': crypto.randomUUID() }
  });
  if (!response.ok) throw new Error('下载失败');
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
}
