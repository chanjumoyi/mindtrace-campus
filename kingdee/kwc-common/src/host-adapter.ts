export type HostUser = {
  id: string;
  username: string;
  displayName: string;
  roles: string[];
  permissions: string[];
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

/**
 * 本地浏览器适配器。正式苍穹环境需要用租户实际 KWC SDK 实现同一接口，
 * 业务组件不得直接依赖未冻结的全局对象或页面字段。
 */
export class BrowserHostAdapter implements KwcHostAdapter {
  getLocale(): string { return document.documentElement.lang || 'zh-CN'; }
  async getAccessToken(): Promise<string> { return sessionStorage.getItem('xinji_token') || ''; }
  async getCurrentUser(): Promise<HostUser> {
    return JSON.parse(sessionStorage.getItem('xinji_user') || '{"id":"","username":"","displayName":"","roles":[],"permissions":[]}');
  }
  navigate(path: string): void { location.hash = `#${path}`; }
  notify(_type: 'success' | 'warning' | 'error' | 'info', message: string): void { window.alert(message); }
  async confirm(message: string): Promise<boolean> { return window.confirm(message); }
  emit(eventName: string, payload: unknown): void { window.dispatchEvent(new CustomEvent(`xinji:${eventName}`, { detail: payload })); }
}
