# 笔迹分析 KWC 业务组件

该目录是角色 A 面向金蝶苍穹的业务组件源代码。它只依赖 `kwc-common` 的生命周期、Host Adapter 和 API Client，不在浏览器保存模型密钥。

当前开发环境先由 `local/frontend` 验证完整交互；苍穹租户环境到位后，需要根据租户实际 KWC SDK：

1. 将 `HandwritingComponent.mount/update/unmount` 映射到官方生命周期；
2. 实现 `KwcHostAdapter` 的令牌、通知和事件方法；
3. 将 `apiBaseUrl` 指向 C 的 Java 网关；
4. 注册 `component-manifest.json` 中的属性与事件。

Qwen API Key 只配置在 Python/苍穹服务端，不得进入 KWC 属性或前端代码。
