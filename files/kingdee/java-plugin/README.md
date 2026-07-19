# 苍穹 Java 插件适配

本目录包含两层：

1. `FoundationPluginCore`：JDK 8、平台无关、可独立编译和自测；负责安全调用 C 网关。
2. `cosmic-template/...java.template`：放入苍穹开发工具生成工程的薄包装层；只适配实际 SDK 事件和视图 API。

验证：

```bash
bash kingdee/java-plugin/scripts/verify-java8.sh
```

核心不依赖未知的苍穹 Maven 坐标，不包含 `UnsupportedOperationException`，也不硬编码服务令牌。完整接入步骤见 `docs/C任务完成与苍穹部署操作手册.md`。
