# 心迹AI KWC 公共组件包

C 维护的生命周期、Host Adapter、API Client、主题和公共壳。包内不包含 A/B 业务页面。

```bash
npm run test
npm run package
```

平台接入时提供 `window.__XINJI_KINGDEE_KWC_BRIDGE__` 的 7 个方法；真实 SDK 名称只出现在租户桥接文件，公共包不写死平台版本。详细步骤见 `docs/C任务完成与苍穹部署操作手册.md`。
