# Android App 构建与交付

Android 工程位于 `frontend/handwriting-collector-mobile/android`，应用标识为 `com.mindtrace.collector`，应用名称为“心迹书写采集”。当前最低支持 Android 7（API 24），目标版本为 Android 16（API 36）。

## 已实现的原生能力

- App 内全屏显示采集界面，不显示浏览器中的手机外框和设备选择器。
- 使用 Android 系统软键盘。
- JSON 先保存在本机采集记录中，再通过 Android 系统分享面板保存到文件、网盘、微信或其他应用。
- 上传沿用现有采集服务器配置，明文 HTTP 仅允许配置中的采集主机；关闭 Android 系统备份。
- 固定竖屏，支持数位笔 Pointer Events 和笔压数据。

## 构建环境

- Node.js 22 或更高版本
- JDK 21
- Android SDK Platform 36
- Android SDK Build-Tools 35 或更高版本
- Android Studio 2025.2.1 或更高版本（推荐）

## 生成测试 APK

```bash
cd frontend/handwriting-collector-mobile
npm ci
npm run android:apk
```

输出文件：

```text
artifacts/android/mindtrace-handwriting-collector-debug.apk
```

Debug APK 可以直接安装到允许“安装未知应用”的测试设备，但它使用开发调试证书，不应作为长期正式发行版本。

通过数据线安装：

```bash
adb install -r artifacts/android/mindtrace-handwriting-collector-debug.apk
```

## 更新网页代码后同步 Android

```bash
npm run android:sync
```

然后用 Android Studio 打开 `android` 目录，或运行：

```bash
npm run android:open
```

## 生成正式签名 APK/AAB

正式分发前应由项目负责人创建并长期保管 Android 签名密钥：

1. 使用 Android Studio 打开 `frontend/handwriting-collector-mobile/android`。
2. 选择 **Build → Generate Signed App Bundle or APK**。
3. 面向组内直接安装可选择 APK；面向应用商店应选择 Android App Bundle（AAB）。
4. 首次发布时创建 `.jks` 密钥库，后续更新必须继续使用同一密钥。
5. 密钥库、别名和密码不得提交到 Git，也不要交给普通采集人员。

建议把正式密钥离线备份两份，并由项目负责人管理。丢失密钥后，已安装的正式 App 将无法正常升级到新版本。

## 发布前验收

1. 在至少一台 Android 手机和平板或带数位笔的设备上安装。
2. 完成初次测试和后续测试各一轮。
3. 验证无接触悬停不会画线，笔压会改变线条粗细。
4. 验证 JSON 文件名包含参与者 ID、`Txxx` 轮次和完成时间。
5. 从分享面板把 JSON 保存到文件管理器，再打开确认内容完整。
6. 卸载重装前先导出数据；当前本机历史记录会随 App 数据清除而消失。

## 与服务器的关系

APK 内置当前前端资源，不依赖网页服务器即可完成本地采集和 JSON 导出。目前会在本机保存后按既有配置尝试上传，失败时可重试；管理员测试记录不上传。更改上传配置需要重新构建发布 App。


## 1.0.1 Android 兼容性更新

- 抄写和自由书写支持双指撤回、三指恢复，并提供“撤回”“恢复”按钮。部分厂商系统手势可能先于 WebView 消费三指触摸，此时可使用恢复按钮；应用不修改系统手势设置。
- 触摸列表用于完整手指数识别，指针捕获变化不再直接取消正常的三指恢复。真实取消、拖动和长按不执行历史编辑。
- 小屏幕或输入法压缩视口时，信息、问卷和结果页面支持纵向滚动。
- 该版本 Android versionCode=2、versionName=1.0.1，最低 API 24。自动化覆盖浏览器触摸与模拟原生 bridge 契约、APK 构建及签名核验；小米 14 Ultra/HyperOS 真机验收仍须在设备上完成。

## 1.0.2 多指计数修复

- 修复同一触摸过程中，手指抬起后重新落下被累计为更多手指、导致撤回或恢复不触发的问题。
- 原生触摸以 `targetTouches` 统计同时接触的手指数；指针抬起后及时移除对应记录。
- Android versionCode=3、versionName=1.0.2。双指/三指重新落指的回归测试同时检查笔迹点数与画布像素；真机效果仍须安装验证。
