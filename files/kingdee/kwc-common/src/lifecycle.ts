import type { KwcHostAdapter } from './host-adapter.js';

export type CommonComponentProps = {
  moduleCode: 'COMMON' | 'HANDWRITING' | 'MULTIMODAL_AGENT' | string;
  apiBaseUrl: string;
  readonly?: boolean;
  recordId?: string;
};

export interface CommonKwcComponent {
  mount(root: HTMLElement, props: CommonComponentProps, host: KwcHostAdapter): Promise<void> | void;
  update(props: CommonComponentProps): Promise<void> | void;
  unmount(): Promise<void> | void;
}

export function assertRoot(root: HTMLElement | null): asserts root is HTMLElement {
  if (!root) throw new Error('KWC root element is required');
}

export function validateProps(props: CommonComponentProps): void {
  if (!props?.moduleCode?.trim()) throw new Error('moduleCode is required');
  if (!props?.apiBaseUrl?.trim()) throw new Error('apiBaseUrl is required');
  const url = new URL(props.apiBaseUrl, window.location.origin);
  if (!['http:', 'https:'].includes(url.protocol)) throw new Error('apiBaseUrl must use http or https');
}
