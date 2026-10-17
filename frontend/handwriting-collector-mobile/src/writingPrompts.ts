export type CopyPrompt = {
  id: string;
  text: string;
  characterCount: number;
};

export type CopyPromptAssignment = CopyPrompt & {
  poolId: "universal_positive";
  poolVersion: string;
  selectionMethod: "crypto_random" | "math_random" | "injected_index";
};

export const COPY_PROMPT_POOL_VERSION = "universal-positive-zh-cn/2.0";

const countCharacters = (text: string) => [...text.replace(/[，。！？；：、\s]/g, "")].length;
const prompt = (id: string, text: string): CopyPrompt => ({ id, text, characterCount: countCharacters(text) });

export const COPY_PROMPT_POOL: readonly CopyPrompt[] = [
  prompt("CP_P_01", "今天的阳光落在窗边，我从容地做好眼前事情。"),
  prompt("CP_P_02", "清晨的微风穿过树叶，我带着期待开始新一天。"),
  prompt("CP_P_03", "温暖的光照亮桌面，我认真记录此刻美好心情。"),
  prompt("CP_P_04", "远处的云朵缓缓移动，我愿意平静地继续前行。"),
  prompt("CP_P_05", "新的想法慢慢出现，我相信努力会带来新收获。"),
  prompt("CP_P_06", "身边的小事充满温度，我珍惜此刻安稳的时光。"),
  prompt("CP_P_07", "今天也有值得期待的事，我会认真走好每一步。"),
  prompt("CP_P_08", "窗外的树叶轻轻摇动，我带着微笑写下这句话。"),
  prompt("CP_P_09", "每一次认真地去尝试，都让我更加接近心中目标。"),
];

export function selectCopyPrompt(injectedIndex?: number): CopyPromptAssignment {
  let index: number;
  let selectionMethod: CopyPromptAssignment["selectionMethod"];
  if (injectedIndex !== undefined) {
    index = Math.abs(Math.trunc(injectedIndex)) % COPY_PROMPT_POOL.length;
    selectionMethod = "injected_index";
  } else if (globalThis.crypto?.getRandomValues) {
    index = globalThis.crypto.getRandomValues(new Uint32Array(1))[0] % COPY_PROMPT_POOL.length;
    selectionMethod = "crypto_random";
  } else {
    index = Math.floor(Math.random() * COPY_PROMPT_POOL.length);
    selectionMethod = "math_random";
  }
  return { ...COPY_PROMPT_POOL[index], poolId: "universal_positive", poolVersion: COPY_PROMPT_POOL_VERSION, selectionMethod };
}
