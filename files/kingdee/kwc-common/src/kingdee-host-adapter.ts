import type { HostUser, KwcHostAdapter } from './host-adapter.js';

/**
 * 苍穹页面只需把租户当前版本提供的 API 映射到这 7 个稳定方法。
 * 这样公共组件不依赖某个未确认版本的全局变量或私有 SDK 名称。
 */
export interface KingdeeKwcBridge {
  getLocale(): string | undefined;
  getAccessToken(): Promise<string> | string;
  getCurrentUser(): Promise<HostUser> | HostUser;
  openPage(path: string): void;
  showMessage(type: 'success' | 'warning' | 'error' | 'info', message: string): void;
  confirm(message: string): Promise<boolean> | boolean;
  fireEvent(eventName: string, payload: unknown): void;
}

declare global {
  interface Window {
    __XINJI_KINGDEE_KWC_BRIDGE__?: KingdeeKwcBridge;
  }
}

export class KingdeeKwcHostAdapter implements KwcHostAdapter {
  constructor(private readonly bridge: KingdeeKwcBridge) {
    if (!bridge) throw new Error('Kingdee KWC bridge is required');
  }

  getLocale(): string { return this.bridge.getLocale() || 'zh-CN'; }
  async getAccessToken(): Promise<string> { return await this.bridge.getAccessToken(); }
  async getCurrentUser(): Promise<HostUser> {
    const user = await this.bridge.getCurrentUser();
    if (!user?.id || !user.username) throw new Error('苍穹 Host Bridge 未返回可信用户身份');
    return {
      id: String(user.id),
      username: String(user.username),
      displayName: String(user.displayName || user.username),
      roles: Array.isArray(user.roles) ? user.roles.map(String) : [],
      permissions: Array.isArray(user.permissions) ? user.permissions.map(String) : [],
      ...(user.organizationId ? { organizationId: String(user.organizationId) } : {})
    };
  }
  navigate(path: string): void { this.bridge.openPage(path); }
  notify(type: 'success' | 'warning' | 'error' | 'info', message: string): void { this.bridge.showMessage(type, message); }
  async confirm(message: string): Promise<boolean> { return Boolean(await this.bridge.confirm(message)); }
  emit(eventName: string, payload: unknown): void { this.bridge.fireEvent(eventName, payload); }
}

export function createKingdeeHostAdapter(bridge?: KingdeeKwcBridge): KingdeeKwcHostAdapter {
  const resolved = bridge || window.__XINJI_KINGDEE_KWC_BRIDGE__;
  if (!resolved) {
    throw new Error('未注入 window.__XINJI_KINGDEE_KWC_BRIDGE__；请按 docs/C任务完成与苍穹部署操作手册.md 完成租户 API 映射');
  }
  return new KingdeeKwcHostAdapter(resolved);
}
