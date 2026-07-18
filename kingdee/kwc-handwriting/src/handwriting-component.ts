import { FoundationApiClient } from '../../kwc-common/src/api-client';
import type { CommonComponentProps, CommonKwcComponent } from '../../kwc-common/src/lifecycle';
import { assertRoot } from '../../kwc-common/src/lifecycle';
import type { KwcHostAdapter } from '../../kwc-common/src/host-adapter';

export type HandwritingComponentProps = CommonComponentProps & {
  apiBaseUrl?: string;
  includeLlm?: boolean;
};

export class HandwritingComponent implements CommonKwcComponent {
  private root?: HTMLElement;
  private props: HandwritingComponentProps = { moduleCode: 'HANDWRITING', includeLlm: true };
  private host?: KwcHostAdapter;
  private abort?: AbortController;

  async mount(root: HTMLElement, props: HandwritingComponentProps, host: KwcHostAdapter): Promise<void> {
    assertRoot(root);
    this.root = root; this.props = { ...this.props, ...props }; this.host = host;
    this.render();
  }

  async update(props: HandwritingComponentProps): Promise<void> {
    this.props = { ...this.props, ...props };
    this.render();
  }

  unmount(): void {
    this.abort?.abort();
    if (this.root) this.root.innerHTML = '';
    this.root = undefined;
  }

  private render(): void {
    if (!this.root) return;
    this.root.innerHTML = `<section class="xj-handwriting"><h2>笔迹观察</h2><p>选择采集器导出的 JSON。结果仅用于书写行为观察。</p><input data-role="trace" type="file" accept="application/json,.json"><button data-role="run" disabled>开始分析</button><pre data-role="result"></pre></section>`;
    const input = this.root.querySelector<HTMLInputElement>('[data-role="trace"]');
    const button = this.root.querySelector<HTMLButtonElement>('[data-role="run"]');
    let trace: unknown;
    input?.addEventListener('change', async () => {
      try { trace = JSON.parse(await input.files![0].text()); if (button) button.disabled = false; }
      catch { this.host?.notify('error', '轨迹 JSON 无法解析'); }
    });
    button?.addEventListener('click', async () => {
      if (!trace || !this.root || !this.host) return;
      const root = this.root;
      const host = this.host;
      button.disabled = true;
      try {
        const client = new FoundationApiClient(this.props.apiBaseUrl || '/api/v1', host);
        const result = await client.request<unknown>('/handwriting/analyze', { method: 'POST', body: JSON.stringify({ trace, includeLlm: this.props.includeLlm !== false }) });
        root.querySelector<HTMLElement>('[data-role="result"]')!.textContent = JSON.stringify(result, null, 2);
        host.emit('handwriting-analysis-completed', result);
      } catch (error) { host.notify('error', error instanceof Error ? error.message : '笔迹分析失败'); }
      finally { button.disabled = false; }
    });
  }
}
