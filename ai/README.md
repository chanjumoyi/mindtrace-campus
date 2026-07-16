# AI资产

```text
ai/
├─ prompts/           # 系统/节点Prompt及版本记录
├─ workflows/         # Agent状态机和编排设计
├─ tools/             # 工具JSON Schema、权限和错误处理
├─ knowledge-base/    # 已审核语料、来源和元数据
├─ eval/              # 离线评测集、评分规则和结果
└─ safety/            # 危机规则、越界策略、提示注入测试
```

Prompt和规则必须版本化。知识库材料必须记录来源、适用范围和审核状态。任何危机测试语料均为人工构造模拟数据。

