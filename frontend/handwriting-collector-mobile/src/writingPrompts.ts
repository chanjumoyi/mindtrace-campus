export type CopyPromptBandId = "range_0_15" | "range_16_31" | "range_32_47" | "range_48_64" | "unscored";

export type CopyPrompt = {
  id: string;
  text: string;
  characterCount: number;
};

export type CopyPromptAssignment = CopyPrompt & {
  bandId: CopyPromptBandId;
  scoreMin: number | null;
  scoreMax: number | null;
  questionnaireSymptomSum: number | null;
  poolVersion: string;
  selectionMethod: "crypto_random" | "math_random" | "injected_index";
};

export const COPY_PROMPT_POOL_VERSION = "copy-prompts-zh-cn/1.0";

const countCharacters = (text: string) => [...text.replace(/[，。！？；：、\s]/g, "")].length;
const prompt = (id: string, text: string): CopyPrompt => ({ id, text, characterCount: countCharacters(text) });

export const COPY_PROMPT_POOLS: Record<CopyPromptBandId, readonly CopyPrompt[]> = {
  range_0_15: [
    prompt("CP_A_01", "今天的阳光落在窗边，我安静地整理眼前的事情。"),
    prompt("CP_A_02", "清晨的风穿过树叶，我按计划完成今天的小事情。"),
    prompt("CP_A_03", "桌上的水杯泛着微光，我从容地写下此刻所见。"),
  ],
  range_16_31: [
    prompt("CP_B_01", "今天有些事情需要处理，我会一步一步慢慢完成。"),
    prompt("CP_B_02", "窗外的声音来来去去，我把注意放回眼前一页。"),
    prompt("CP_B_03", "行程偶尔会被打乱，我仍可以安排接下来的事情。"),
  ],
  range_32_47: [
    prompt("CP_C_01", "面对接连出现的事情，我先停一下再逐项去处理。"),
    prompt("CP_C_02", "思绪来回变化的时候，我把此刻的感受写在纸上。"),
    prompt("CP_C_03", "今天可能有些不容易，我允许自己按照节奏前进。"),
  ],
  range_48_64: [
    prompt("CP_D_01", "当许多感受同时出现，我先关注呼吸和眼前一步。"),
    prompt("CP_D_02", "此刻如果感到很辛苦，我可以慢慢写下真实体验。"),
    prompt("CP_D_03", "今天先完成眼前这句话，再决定接下来要做什么。"),
  ],
  unscored: [
    prompt("CP_U_01", "窗边的光线缓缓移动，我认真写下眼前这句话。"),
    prompt("CP_U_02", "桌面上的物品安静摆放，我按照顺序完成书写。"),
    prompt("CP_U_03", "远处的声音轻轻传来，我保持平常速度写下去。"),
  ],
};

export function getCopyPromptBand(score: number | null): { bandId: CopyPromptBandId; scoreMin: number | null; scoreMax: number | null } {
  if (score === null || !Number.isFinite(score)) return { bandId: "unscored", scoreMin: null, scoreMax: null };
  if (score <= 15) return { bandId: "range_0_15", scoreMin: 0, scoreMax: 15 };
  if (score <= 31) return { bandId: "range_16_31", scoreMin: 16, scoreMax: 31 };
  if (score <= 47) return { bandId: "range_32_47", scoreMin: 32, scoreMax: 47 };
  return { bandId: "range_48_64", scoreMin: 48, scoreMax: 64 };
}

export function selectCopyPrompt(score: number | null, injectedIndex?: number): CopyPromptAssignment {
  const band = getCopyPromptBand(score);
  const pool = COPY_PROMPT_POOLS[band.bandId];
  let index: number;
  let selectionMethod: CopyPromptAssignment["selectionMethod"];
  if (injectedIndex !== undefined) {
    index = Math.abs(Math.trunc(injectedIndex)) % pool.length;
    selectionMethod = "injected_index";
  } else if (globalThis.crypto?.getRandomValues) {
    index = globalThis.crypto.getRandomValues(new Uint32Array(1))[0] % pool.length;
    selectionMethod = "crypto_random";
  } else {
    index = Math.floor(Math.random() * pool.length);
    selectionMethod = "math_random";
  }
  return { ...pool[index], ...band, questionnaireSymptomSum: score, poolVersion: COPY_PROMPT_POOL_VERSION, selectionMethod };
}
