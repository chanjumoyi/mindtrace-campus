export type HostUser = {
  id: string;
  username: string;
  displayName: string;
  roles: string[];
  permissions: string[];
  organizationId?: string;
};

export interface KwcHostAdapter {
  getLocale(): string;
  getAccessToken(): Promise<string>;
  getCurrentUser(): Promise<HostUser>;
  navigate(path: string): void;
  notify(type: 'success' | 'warning' | 'error' | 'info', message: string): void;
  confirm(message: string): Promise<boolean>;
  emit(eventName: string, payload: unknown): void;
}

export class BrowserHostAdapter implements KwcHostAdapter {
  getLocale(): string { return document.documentElement.lang || 'zh-CN'; }
  async getAccessToken(): Promise<string> { return sessionStorage.getItem('xinji_token') || ''; }
  async getCurrentUser(): Promise<HostUser> {
    const fallback: HostUser = { id: '', username: '', displayName: '', roles: [], permissions: [] };
    const raw = sessionStorage.getItem('xinji_user');
    if (!raw) return fallback;
    try { return { ...fallback, ...JSON.parse(raw) as Partial<HostUser> }; }
    catch { return fallback; }
  }
  navigate(path: string): void { location.hash = `#${path}`; }
  notify(_type: 'success' | 'warning' | 'error' | 'info', message: string): void { window.alert(message); }
  async confirm(message: string): Promise<boolean> { return window.confirm(message); }
  emit(eventName: string, payload: unknown): void {
    window.dispatchEvent(new CustomEvent(`xinji:${eventName}`, { detail: payload }));
  }
}
