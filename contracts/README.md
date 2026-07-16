# 接口契约

```text
contracts/
├─ openapi/       # REST/服务模型接口
├─ schemas/       # Agent工具、事件和DTO的JSON Schema
├─ errors/        # 统一错误码
└─ mappings/      # 概念模型—苍穹实体—数据库—API字段映射
```

约定：先改契约并评审，再修改本地Adapter、Java插件、KWC和Agent工具。所有写操作声明鉴权、幂等和审计要求。

