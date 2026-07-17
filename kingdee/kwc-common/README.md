# KWC 公共组件规范（C）

这里提供平台无关的生命周期、Host Adapter、API Client、主题 Token、错误与事件规范。A/B 的业务组件应依赖这些公共接口，但各自维护自己的页面和逻辑。

## 约束

1. 组件不得在浏览器保存模型密钥。
2. 组件不得执行最终风险判断。
3. 写操作必须携带 `Idempotency-Key`；所有请求携带 `X-Request-Id`。
4. 敏感正文不得放进 URL、埋点或控制台日志。
5. A 使用 `moduleCode=HANDWRITING`；B 使用 `moduleCode=MULTIMODAL_AGENT`；公共页面使用 `COMMON`。
6. 正式苍穹 KWC SDK 的生命周期名称和注册入口必须以比赛租户实际版本为准；只需实现 `KwcHostAdapter`，其余公共组件无需改动。

## 生命周期

```text
平台创建组件 -> mount(root, props, host)
属性变化     -> update(props)
页面销毁     -> unmount()
```

`component-manifest.example.json` 是字段与事件清单，不冒充特定版本的官方安装格式。环境到位后按 `docs/苍穹部署与迁移.md` 映射。
