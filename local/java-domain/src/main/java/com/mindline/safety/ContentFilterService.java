package com.mindline.safety;

import java.util.*;
import java.util.regex.Pattern;

/**
 * 内容安全过滤器 —— Agent输出的后处理和用户输入的安全预检查。
 *
 * <p>执行三个层级的过滤：
 * <ol>
 *   <li>诊断术语替换 —— 将可能被误解为诊断的术语替换为中性表述</li>
 *   <li>PII模式检测 —— 检测和掩盖手机号、身份证号、邮箱等</li>
 *   <li>安全预检查 —— 检测用户输入中的自伤/自杀/暴力关键词</li>
 * </ol>
 *
 * <p>所有修改操作均记录审计日志。
 */
public class ContentFilterService {

    // 诊断术语 → 中性替换
    private static final Map<String, String> DIAGNOSTIC_TERMS = new LinkedHashMap<>();
    static {
        DIAGNOSTIC_TERMS.put("可能患有抑郁症", "可能存在持续的情绪困扰");
        DIAGNOSTIC_TERMS.put("可能患有焦虑症", "可能存在明显的焦虑表现");
        DIAGNOSTIC_TERMS.put("抑郁症患者", "正在经历抑郁情绪的人");
        DIAGNOSTIC_TERMS.put("焦虑症", "焦虑状态");
        DIAGNOSTIC_TERMS.put("强迫症", "强迫倾向");
        DIAGNOSTIC_TERMS.put("创伤后应激障碍", "创伤后心理反应");
        DIAGNOSTIC_TERMS.put("人格障碍", "人格特质倾向");
        DIAGNOSTIC_TERMS.put("精神分裂", "思维困扰");
        DIAGNOSTIC_TERMS.put("双相情感障碍", "情绪波动困扰");
        DIAGNOSTIC_TERMS.put("自闭症", "社交沟通差异");
        DIAGNOSTIC_TERMS.put("多动症", "注意力调节困难");
        DIAGNOSTIC_TERMS.put("心理疾病", "心理健康困扰");
        DIAGNOSTIC_TERMS.put("精神疾病", "心理健康议题");
        DIAGNOSTIC_TERMS.put("症状", "表现");  // 谨慎使用，保留"常见表现"等非诊断用法
    }

    // PII正则模式
    private static final Pattern PHONE_PATTERN = Pattern.compile("1[3-9]\\d{9}");
    private static final Pattern ID_CARD_PATTERN = Pattern.compile("\\d{17}[\\dXx]");
    private static final Pattern EMAIL_PATTERN = Pattern.compile("[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}");

    // 安全预检查关键词
    private static final List<String> CRISIS_KEYWORDS = List.of(
            "想死", "不想活", "自杀", "结束生命", "自残", "割腕",
            "跳楼", "上吊", "安眠药自杀", "去死",
            "杀人", "伤害他人", "报复社会",
            "活不下去了", "没有意义", "绝望透顶", "无路可走"
    );

    private final List<FilterRecord> filterLog = new ArrayList<>();

    /**
     * 对Agent输出进行诊断术语过滤。
     *
     * @param text 原始Agent输出文本
     * @return 过滤后的安全文本
     */
    public FilterResult filterDiagnosticTerms(String text) {
        String filtered = text;
        List<String> replacements = new ArrayList<>();

        for (Map.Entry<String, String> entry : DIAGNOSTIC_TERMS.entrySet()) {
            if (filtered.contains(entry.getKey())) {
                filtered = filtered.replace(entry.getKey(), entry.getValue());
                replacements.add(entry.getKey() + " → " + entry.getValue());
            }
        }

        if (!replacements.isEmpty()) {
            filterLog.add(new FilterRecord("diagnostic-term", text, filtered,
                    String.join("; ", replacements)));
        }

        return new FilterResult(filtered, replacements.isEmpty(), replacements);
    }

    /**
     * 检测并掩盖文本中的PII模式。
     *
     * @param text 待检测文本
     * @return 脱敏后的文本
     */
    public FilterResult maskPII(String text) {
        String filtered = text;
        List<String> detections = new ArrayList<>();

        if (PHONE_PATTERN.matcher(filtered).find()) {
            filtered = PHONE_PATTERN.matcher(filtered).replaceAll("[手机号已隐藏]");
            detections.add("phone-number");
        }
        if (ID_CARD_PATTERN.matcher(filtered).find()) {
            filtered = ID_CARD_PATTERN.matcher(filtered).replaceAll("[身份证号已隐藏]");
            detections.add("id-card");
        }
        if (EMAIL_PATTERN.matcher(filtered).find()) {
            filtered = EMAIL_PATTERN.matcher(filtered).replaceAll("[邮箱已隐藏]");
            detections.add("email");
        }

        if (!detections.isEmpty()) {
            filterLog.add(new FilterRecord("pii-mask", text, filtered,
                    String.join(", ", detections)));
        }

        return new FilterResult(filtered, detections.isEmpty(), detections);
    }

    /**
     * 用户输入安全预检查 —— 检测危机信号。
     *
     * @param userInput 用户输入文本
     * @return 安全检查结果。isCrisis=true时需要触发安全响应而非正常分析。
     */
    public SafetyCheckResult safetyPreCheck(String userInput) {
        if (userInput == null || userInput.isEmpty()) {
            return SafetyCheckResult.SAFE;
        }

        String lower = userInput.toLowerCase();
        List<String> matchedKeywords = new ArrayList<>();

        for (String keyword : CRISIS_KEYWORDS) {
            if (lower.contains(keyword)) {
                matchedKeywords.add(keyword);
            }
        }

        if (!matchedKeywords.isEmpty()) {
            filterLog.add(new FilterRecord("crisis-detected", userInput,
                    "SAFETY_RESPONSE_TRIGGERED", String.join(", ", matchedKeywords)));
            return new SafetyCheckResult(true, matchedKeywords,
                    buildSafetyResponse());
        }

        return SafetyCheckResult.SAFE;
    }

    /**
     * 对Agent输出的完整内容安全检查流水线。
     */
    public FilterResult fullContentCheck(String agentOutput) {
        FilterResult piiResult = maskPII(agentOutput);
        FilterResult termResult = filterDiagnosticTerms(piiResult.getFiltered());
        return termResult;
    }

    /**
     * 获取过滤日志（用于审计）。
     */
    public List<FilterRecord> getFilterLog() {
        return Collections.unmodifiableList(filterLog);
    }

    /**
     * 清空过滤日志。
     */
    public void clearLog() {
        filterLog.clear();
    }

    private String buildSafetyResponse() {
        return """
                我们注意到你的表达中有一些让人担心的内容。

                作为一个辅助探索工具，心迹AI无法提供危机支持。如果你正在经历困难的时刻：

                • 联系学校心理咨询中心
                • 全国心理援助热线：400-161-9995（24小时）
                • 全国希望24热线：400-161-9995
                • 告诉身边你信任的人

                你不需要独自面对这些。""";
    }

    // ---- 内部类 ----

    /** 过滤结果 */
    public static class FilterResult {
        private final String filtered;
        private final boolean clean;  // true = 无修改
        private final List<String> details;

        public FilterResult(String filtered, boolean clean, List<String> details) {
            this.filtered = filtered;
            this.clean = clean;
            this.details = details;
        }

        public String getFiltered() { return filtered; }
        public boolean isClean() { return clean; }
        public List<String> getDetails() { return details; }
    }

    /** 安全检查结果 */
    public static class SafetyCheckResult {
        public static final SafetyCheckResult SAFE = new SafetyCheckResult(false, List.of(), null);

        private final boolean crisis;
        private final List<String> matchedKeywords;
        private final String safetyMessage;

        public SafetyCheckResult(boolean crisis, List<String> matchedKeywords, String safetyMessage) {
            this.crisis = crisis;
            this.matchedKeywords = matchedKeywords;
            this.safetyMessage = safetyMessage;
        }

        public boolean isCrisis() { return crisis; }
        public List<String> getMatchedKeywords() { return matchedKeywords; }
        public String getSafetyMessage() { return safetyMessage; }
    }

    /** 过滤记录（审计用） */
    public record FilterRecord(String rule, String original, String filtered, String detail) {}
}
