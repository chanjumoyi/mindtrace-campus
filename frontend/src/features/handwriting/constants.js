export const QUESTIONNAIRE_ITEMS = [
  {
    id: 'stressLevel',
    title: '此刻，你感受到的压力程度是？',
    hint: '请选择最接近当下感受的一项',
    min: 1,
    max: 5,
    lowLabel: '几乎没有',
    highLabel: '非常明显',
  },
  {
    id: 'moodLevel',
    title: '此刻，你的整体心情如何？',
    hint: '不需要反复斟酌，按第一感受选择即可',
    min: 1,
    max: 5,
    lowLabel: '比较低落',
    highLabel: '比较愉快',
  },
  {
    id: 'fatigueLevel',
    title: '此刻，你感觉有多疲劳？',
    hint: '包括身体疲劳和注意力疲劳',
    min: 1,
    max: 5,
    lowLabel: '精力充足',
    highLabel: '非常疲劳',
  },
  {
    id: 'sleepQuality',
    title: '你觉得昨晚的睡眠质量如何？',
    hint: '按照自己的主观感受选择',
    min: 1,
    max: 5,
    lowLabel: '很差',
    highLabel: '很好',
  },
]

export const WRITING_TASKS = [
  {
    code: 'PRESS_CHECK',
    type: 'free_writing',
    title: '压感检查',
    prompt: '请用自然力度，从左到右画三条短横线。',
    guidance: '三条线可以使用稍有区别的力度，用于确认设备是否能读取压力变化。',
  },
  {
    code: 'COPY',
    type: 'copy_text',
    title: '固定句抄写',
    prompt: '今天的风很轻，我按自己的节奏完成了手中的事情。',
    guidance: '请按平时的速度自然书写，不需要刻意写得工整。',
  },
  {
    code: 'FREE',
    type: 'free_writing',
    title: '自由书写',
    prompt: '请写下今天让你印象较深的一件小事，以及当时的感受。',
    guidance: '建议写 30～80 字；请勿填写姓名、学号、联系方式或他人隐私。',
  },
]

export const NOTICE_VERSION = 'offline-collection-v1'
