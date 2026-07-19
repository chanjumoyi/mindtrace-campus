# 平台原生导出物放置区

这里必须放入你在登录后的苍穹开发环境中导出的原生资产，例如领域模型、服务模型、KWC 注册、Java 插件、Agent 工具和产品安装包。

仓库脚本不会伪造这些二进制或租户专属文件。完成平台操作后：

1. 将导出文件放入本目录；
2. 在 `environment.local.yaml` 填写 `productPackage.nativeExportFile`；
3. 执行 `python3 kingdee/deployment/preflight.py kingdee/deployment/environment.local.yaml --require-native-export`；
4. 再执行 `python3 kingdee/deployment/build_c_delivery.py --environment kingdee/deployment/environment.local.yaml --include-native-export`。

不要提交包含真实密钥、Cookie、租户访问令牌或个人数据的导出物。
