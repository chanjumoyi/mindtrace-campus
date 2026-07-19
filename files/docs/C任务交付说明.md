# C 任务交付说明

版本：1.1.0
范围：只包含 C 的公共框架、Java 网关、数据库、权限与审计、AI 调用治理、KWC 公共组件、苍穹适配、部署和验收资产。

## 已完成的代码

- AI 请求级总超时、单次尝试超时、可重试错误分类、指数退避、抖动和 `Retry-After`。
- 完成结果回放、请求冲突检测、处理中租约、失败恢复、过期恢复和定时清理。
- PostgreSQL 共享固定窗口限流，响应 `Retry-After` 与 `X-RateLimit-Limit`。
- 调用日志、逐次尝试日志、回放关系、错误脱敏、审计记录和 Micrometer 指标。
- 苍穹服务账号令牌与最小权限认证。
- KWC TypeScript 构建、生命周期、API Client、7 方法 Host Bridge、主题、测试、校验和和打包。
- Java 8 平台无关插件核心、苍穹薄包装模板、路径白名单、超时、响应大小限制和自测。
- 9 个 C 公共领域模型、3 个 C Agent 工具、导入 CSV/JSON、权限工作表和 SHA-256 清单。
- 环境预检、C-only 交付组包、静态/安全/契约测试和在线 E2E 脚本。

## 未伪造的平台结果

以下内容必须在有权限的真实苍穹租户中完成，不能由离线源码替代：

- 确认租户、KWC、Java SDK、Agent 平台和产品包版本。
- 将 7 个 Host Bridge 方法映射到该租户版本的真实 KWC API。
- 在苍穹生成工程中编译并发布薄 Java 插件。
- 创建或导入 9 个模型、配置四类角色、注册 3 个工具。
- 导出苍穹原生产品包，并在第二个干净租户安装、E2E 和回滚。

详细步骤见 `docs/C任务完成与苍穹部署操作手册.md`。

## 验证命令

```bash
python3 tests/run_c_verification.py
```

Maven 和在线环境可用时执行严格验收：

```bash
python3 tests/run_c_verification.py --require-backend --require-live-e2e
```

`SKIPPED` 不等于 `PASSED`。验收结果在 `deliverables/test-report/c-verification-report.json`。
