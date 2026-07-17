import type { KwcHostAdapter } from './host-adapter';

export type CommonComponentProps = {
  moduleCode: 'COMMON' | 'HANDWRITING' | 'MULTIMODAL_AGENT' | string;
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
