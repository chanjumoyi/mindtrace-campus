export function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>'"]/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[ch]));
}

export function statusBadge(status) {
  const normalized = String(status || 'UNKNOWN').toUpperCase();
  return `<span class="badge badge-${normalized.toLowerCase()}">${escapeHtml(normalized)}</span>`;
}

export function emptyState(title, detail='') {
  return `<div class="empty"><strong>${escapeHtml(title)}</strong>${detail ? `<p>${escapeHtml(detail)}</p>` : ''}</div>`;
}

export function pageHeader(title, subtitle, actions='') {
  return `<div class="page-header"><div><h1>${escapeHtml(title)}</h1><p>${escapeHtml(subtitle)}</p></div><div class="page-actions">${actions}</div></div>`;
}

export function toast(message, type='info') {
  const root = document.querySelector('#toast-root');
  const el = document.createElement('div');
  el.className = `toast toast-${type}`;
  el.textContent = message;
  root.appendChild(el);
  setTimeout(() => el.remove(), 3200);
}

export function formatDate(value) {
  if (!value) return '-';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'short' }).format(date);
}

export function skeleton(lines=4) {
  return `<div class="skeleton-wrap">${Array.from({length:lines},()=>'<div class="skeleton"></div>').join('')}</div>`;
}
