// Input sanitization — length enforcement + prompt injection pattern removal

const MAX_INPUT_LENGTH = 1200;

const INJECTION_PATTERNS = [
  /忽略[以之]?[上前][的所]?[有全]?[部]?[指命][示令]/gi,  // "忽略以上所有指令" variants
  /ignore\s+(all\s+)?(previous|above)\s+(instructions?|prompts?)/gi,
  /<\|im_start\|>/gi,       // ChatML delimiter injection
  /<\|im_end\|>/gi,
  /system\s*:\s*(you are|你现在|你的角色)/gi,
  /\[system\]\s*\(/gi,
  /你(\s*)是(\s*)(一个|个|ChatGPT|GPT|AI助手)/gi,  // Role confusion
  /现在起.*你(\s*)是/gi,
  /forget\s+(all\s+)?(previous|above|your)\s+(instructions?|prompts?|training)/gi,
  /pretend\s+(you\s+are|to\s+be)/gi,
  /DAN\s*(mode|模式)/gi,   // Jailbreak patterns
  /developer\s*mode/gi,
];

export function sanitizeInput(text) {
  if (!text || typeof text !== 'string') return { sanitized: '', truncated: false, sanitizedCount: 0 };

  let result = text;
  let sanitizedCount = 0;

  // 1. Length enforcement
  if (result.length > MAX_INPUT_LENGTH) {
    result = result.slice(0, MAX_INPUT_LENGTH);
  }

  // 2. Pattern removal
  for (const pattern of INJECTION_PATTERNS) {
    const before = result.length;
    result = result.replace(pattern, '[已过滤]');
    if (result.length !== before) sanitizedCount++;
  }

  return {
    sanitized: result,
    truncated: text.length > MAX_INPUT_LENGTH,
    sanitizedCount,
  };
}
