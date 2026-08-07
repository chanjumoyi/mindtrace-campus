const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1'

export async function api(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  })
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}))
    throw new Error(payload.detail || payload.message || `请求失败（${response.status}）`)
  }
  return response.json()
}
