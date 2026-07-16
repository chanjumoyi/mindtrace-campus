package com.mindline.platform;

/**
 * 平台适配器工厂 —— 根据配置选择LocalMockAdapter或KingdeeAdapter。
 *
 * <p>使用方式：
 * <pre>{@code
 * PlatformAdapter adapter = PlatformAdapterFactory.create("local");
 * // or via system property: -Dapp.platform.mode=local
 * PlatformAdapter adapter = PlatformAdapterFactory.createFromSystemProperty();
 * }</pre>
 */
public class PlatformAdapterFactory {

    private PlatformAdapterFactory() {
        // 工具类，禁止实例化
    }

    /**
     * 根据模式字符串创建适配器。
     *
     * @param mode "local" 或 "kingdee"
     * @return 对应的PlatformAdapter实现
     * @throws IllegalArgumentException 未知模式
     */
    public static PlatformAdapter create(String mode) {
        return switch (mode.toLowerCase()) {
            case "local" -> new LocalMockAdapter();
            case "kingdee" -> throw new UnsupportedOperationException(
                    "KingdeeAdapter 需在苍穹环境到位后实现。当前仅支持 local 模式。");
            default -> throw new IllegalArgumentException(
                    "未知平台模式: " + mode + "，可选值: local, kingdee");
        };
    }

    /**
     * 从系统属性 app.platform.mode 读取模式并创建适配器。
     * 默认值为 "local"。
     */
    public static PlatformAdapter createFromSystemProperty() {
        String mode = System.getProperty("app.platform.mode", "local");
        return create(mode);
    }
}
