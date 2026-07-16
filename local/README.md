# 本地研发区

本地代码用于快速验证，不取代金蝶AI苍穹核心底座。

```text
local/
├─ java-domain/       # 纯Java领域逻辑：风险规则、趋势、脱敏、指标
├─ mock-service/      # 模拟苍穹流程和Agent工具的联调服务
├─ frontend-prototype/# 页面/交互原型；可复用部分迁往KWC
└─ ai-lab/            # Prompt、RAG和多模态离线实验
```

应通过Adapter隔离平台差异。可复用的是领域逻辑、DTO、契约、测试和交互逻辑；本地模拟服务不得被包装成正式比赛核心实现。

