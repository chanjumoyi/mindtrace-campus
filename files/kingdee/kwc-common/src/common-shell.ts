import { FoundationApiClient } from './api-client.js';
import type { KwcHostAdapter, HostUser } from './host-adapter.js';
import type { CommonComponentProps, CommonKwcComponent } from './lifecycle.js';
import { assertRoot, validateProps } from './lifecycle.js';

type PublicInfo = { name?: string; version?: string; environment?: string };

export class CommonShellComponent implements CommonKwcComponent {
  private root: HTMLElement | undefined;
  private host: KwcHostAdapter | undefined;
  private props: CommonComponentProps | undefined;
  private user: HostUser | undefined;

  async mount(root: HTMLElement, props: CommonComponentProps, host: KwcHostAdapter): Promise<void> {
    assertRoot(root);
    validateProps(props);
    this.root = root;
    this.host = host;
    this.props = props;
    this.user = await host.getCurrentUser();
    await this.render();
    host.emit('ready', { moduleCode: props.moduleCode, userId: this.user.id });
  }

  async update(props: CommonComponentProps): Promise<void> {
    validateProps(props);
    this.props = props;
    await this.render();
  }

  unmount(): void {
    if (this.root) this.root.replaceChildren();
    this.root = undefined;
    this.host = undefined;
    this.props = undefined;
    this.user = undefined;
  }

  private async render(): Promise<void> {
    if (!this.root || !this.host || !this.props || !this.user) return;
    const client = new FoundationApiClient(this.props.apiBaseUrl, this.host);
    let publicInfo: PublicInfo = {};
    try { publicInfo = await client.request<PublicInfo>('/api/v1/public/info', { timeoutMs: 5000 }); }
    catch (error) { this.host.emit('error', { stage: 'public-info', message: error instanceof Error ? error.message : String(error) }); }

    const container = document.createElement('section');
    container.className = 'xj-common-shell';
    container.setAttribute('data-module-code', this.props.moduleCode);

    const title = document.createElement('h2');
    title.textContent = publicInfo.name || '心迹AI';
    const meta = document.createElement('p');
    meta.className = 'xj-common-shell__meta';
    meta.textContent = `${this.user.displayName} · ${this.props.moduleCode}${publicInfo.version ? ` · v${publicInfo.version}` : ''}`;
    const status = document.createElement('span');
    status.className = 'xj-common-shell__status';
    status.textContent = this.props.readonly ? '只读' : '可操作';

    container.append(title, meta, status);
    this.root.replaceChildren(container);
  }
}
