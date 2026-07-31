// Crisis keyword scanner — deterministic, no LLM dependency
// Maps keyword patterns to risk levels: RED (immediate block), ORANGE (concern note), YELLOW (mild flag)

const RED_KEYWORDS = [
  '想死', '自杀', '杀了我', '不想活了', '结束生命', '自残',
  '伤害自己', 'kill myself', 'suicide', '我要去死',
  '活不下去了', '死了算了', '一死了之', '自我了断',
];

const ORANGE_KEYWORDS = [
  '活着没意义', '我受不了了', '撑不下去了', '没人会在乎',
  '消失算了', '没有意义', '好想消失', '不想醒来',
  '活着好累', '不知道为什么要活着',
];

const YELLOW_KEYWORDS = [
  '压力好大', '快崩溃了', '撑不住了', '好绝望',
  '好孤独', '没人理解', '很无力',
];

export function scanCrisis(text) {
  if (!text || typeof text !== 'string') {
    return { level: null, keywords: [] };
  }

  const input = text.toLowerCase();

  // Check RED first (highest priority)
  const redHits = RED_KEYWORDS.filter(kw => input.includes(kw.toLowerCase()));
  if (redHits.length > 0) {
    return { level: 'RED', keywords: redHits };
  }

  // Check ORANGE
  const orangeHits = ORANGE_KEYWORDS.filter(kw => input.includes(kw.toLowerCase()));
  if (orangeHits.length > 0) {
    return { level: 'ORANGE', keywords: orangeHits };
  }

  // Check YELLOW
  const yellowHits = YELLOW_KEYWORDS.filter(kw => input.includes(kw.toLowerCase()));
  if (yellowHits.length > 0) {
    return { level: 'YELLOW', keywords: yellowHits };
  }

  return { level: null, keywords: [] };
}

export const SAFETY_GUIDANCE = [
  '我注意到你正在经历一些非常艰难的感受。你并不孤单——有很多人和资源可以支持你。',
  '',
  '如果你有立即伤害自己或他人的风险，请优先联系：',
  '- 校园心理咨询中心（工作日 8:00-17:00）',
  '- 全国心理援助热线：12355',
  '- 生命热线：400-821-1215（24小时）',
  '- 紧急情况：拨打 110 或 120',
  '',
  '你值得被听见，也值得被帮助。',
].join('\n');
