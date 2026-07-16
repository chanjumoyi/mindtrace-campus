# 测试资产

```text
tests/
├─ unit/           # Java领域逻辑与规则
├─ contract/       # OpenAPI/JSON Schema
├─ integration/    # PostgreSQL、Mock Adapter、苍穹联调
├─ e2e/            # 两条核心业务闭环
├─ ai-eval/        # RAG、Agent、工具调用和安全评测
└─ security/       # 权限、注入、泄漏和审计测试
```

测试用例只使用 `data/mock/` 中的模拟数据。高风险流程必须覆盖漏报、误报、重复建单、工具超时和人工接管。

