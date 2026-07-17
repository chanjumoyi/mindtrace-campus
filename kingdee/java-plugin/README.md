# 苍穹 Java 插件适配

`FoundationPluginCore` 是可独立编译的 JDK 17 核心，负责调用 C 的统一网关、传递 requestId/幂等键并限制可访问路径。

未直接编写某个苍穹 SDK 基类，是因为项目文档明确要求“以官方环境支持版本为准”，而当前未提供租户版本、SDK JAR、插件接口或 Maven 坐标。仓库不伪造这些信息。取得环境后只需要：

1. 在苍穹开发工具生成最小 Java 插件。
2. 将 `FoundationPluginCore.java` 放入插件工程。
3. 按 `PluginEntryTemplate.java.txt` 编写很薄的平台包装层。
4. 从平台密钥管理读取网关服务令牌，禁止硬编码。
5. 按 `contracts/openapi.yaml` 完成字段映射并部署验证。

业务规则、鉴权、幂等、日志和数据持久化均已在网关实现，不应在包装层重复实现。
