package com.mindline.platform;

import com.mindline.model.*;

import java.time.Instant;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * 本地Mock适配器 —— 返回符合生产Schema的固定模拟数据。
 *
 * <p>所有方法返回预定义的、结构完整的Mock响应，使本地开发环境可以
 * 在不依赖苍穹平台的条件下跑通完整业务链路。
 *
 * <p>Mock数据均标注为"模拟"，零真实学生信息。
 */
public class LocalMockAdapter implements PlatformAdapter {

    private final Map<String, Map<String, Object>> savedRecords = new ConcurrentHashMap<>();

    @Override
    public SandplayAgentAnalysis analyzeSandplay(SandplayAnalysisRequest request) {
        // 模拟Agent分析延迟
        simulateLatency(800);

        SandplayAgentAnalysis analysis = new SandplayAgentAnalysis();
        analysis.setThemeSummary(buildThemeSummary(request));
        analysis.setExplorationQuestions(Arrays.asList(
                "你的沙盘中" + getDominantCategory(request) + "类元素较多，它们对你来说有什么特别的意义吗？",
                "你注意到画面中有些区域比较空，有些区域比较密集，这种布局反映了你什么样的状态？",
                "如果把沙盘看作你内心世界的映射，这个场景在讲述什么故事？"
        ));
        analysis.setDisclaimer("仅供自我探索和辅助参考，不构成心理诊断。本分析由本地Mock Agent生成，用于开发测试。");
        analysis.setCitations(Arrays.asList(
                new Citation("sand-ref-001", "沙盘游戏基础方法", "沙盘是来访者内心世界的外在投射..."),
                new Citation("sand-ref-002", "沙盘元素常见象征", "树木通常代表生命力和成长...")
        ));
        return analysis;
    }

    @Override
    public HTPAgentAnalysis analyzeHTP(HTPAnalysisRequest request) {
        simulateLatency(600);

        HTPAgentAnalysis analysis = new HTPAgentAnalysis();
        boolean hasVisualObs = request.getVisualObservation() != null;

        analysis.setObservations(hasVisualObs
                ? "根据画作观察："
                    + (request.getVisualObservation().getHouseDescription() != null ? request.getVisualObservation().getHouseDescription() + " " : "")
                    + (request.getVisualObservation().getTreeDescription() != null ? request.getVisualObservation().getTreeDescription() + " " : "")
                    + (request.getVisualObservation().getPersonDescription() != null ? request.getVisualObservation().getPersonDescription() : "")
                : "图像分析暂不可用，以下分析仅基于问卷信息。");

        StringBuilder interpretation = new StringBuilder();
        interpretation.append("绘制顺序：").append(translateDrawingOrder(request.getDrawingOrder())).append("；");
        interpretation.append("完整度自评：").append(translateCompleteness(request.getCompleteness())).append("。");
        if (request.getHouseDescription() != null && !request.getHouseDescription().isEmpty()) {
            interpretation.append("关于房子，你提到：").append(request.getHouseDescription()).append(" ");
        }
        if (request.getTreeDescription() != null && !request.getTreeDescription().isEmpty()) {
            interpretation.append("关于树，你提到：").append(request.getTreeDescription()).append(" ");
        }
        if (request.getPersonDescription() != null && !request.getPersonDescription().isEmpty()) {
            interpretation.append("关于人，你提到：").append(request.getPersonDescription());
        }
        analysis.setUserInterpretation(interpretation.toString());

        analysis.setExplorationPrompts(Arrays.asList(
                "你在画房子/树/人时，哪一个元素让你花了最多心思？为什么？",
                "如果让你给这幅画加一个元素，你会加什么？放在哪里？",
                "画中的场景是动态的还是静态的？这让你联想到生活中的什么状态？"
        ));
        analysis.setDisclaimer("房树人分析仅作为自我探索的辅助工具，不具有诊断意义。本分析由本地Mock Agent生成，用于开发测试。");
        analysis.setAiInferenceNote("以上部分内容为AI基于用户描述和画面观察的辅助推测，仅供参考和自我探索");
        analysis.setCitations(Arrays.asList(
                new Citation("htp-ref-001", "房树人测验方法论概述", "HTP测验由Buck于1948年提出..."),
                new Citation("htp-ref-002", "房树人解释的边界与争议", "房树人测验的解释效度存在争议...")
        ));
        return analysis;
    }

    @Override
    public VisualObservation describeImage(String imageRef) {
        if (imageRef == null || imageRef.isEmpty()) {
            return null;
        }
        simulateLatency(1200);

        VisualObservation obs = new VisualObservation();
        obs.setHouseDescription("画面中可见一栋房屋，方形结构，有三角形屋顶和烟囱，有门但窗户较小。");
        obs.setTreeDescription("房屋右侧有一棵大树，树冠茂密呈圆形，树干粗壮，无可见果实或落叶。");
        obs.setPersonDescription("画面左下角有一个小型人物形象，站姿，双臂下垂，五官轮廓模糊。");
        obs.setOverallPlacement("三个元素集中在画面中下部，上方约1/3区域留白较多。元素之间的比例关系不太协调（人物明显小于房屋）。");
        obs.setNotableFeatures(Arrays.asList(
                "房屋窗户数量少且尺寸较小",
                "人物尺寸显著小于房屋和树木",
                "画面上方有较大面积留白",
                "三个元素均落在地平线以上"
        ));
        return obs;
    }

    @Override
    public List<Citation> retrieveKnowledge(String topic, String query, int maxResults) {
        // Mock RAG：返回固定引用
        if ("sandplay".equals(topic)) {
            return Arrays.asList(
                    new Citation("sand-ref-001", "沙盘游戏基础方法", "沙盘游戏是一种非语言的心理治疗技术..."),
                    new Citation("sand-ref-003", "沙盘空间象征", "沙盘空间的不同区域可能对应不同的心理内容...")
            );
        } else if ("htp".equals(topic)) {
            return Arrays.asList(
                    new Citation("htp-ref-001", "房树人测验方法论概述", "HTP测验通过分析个体对房屋、树木和人物的绘画..."),
                    new Citation("htp-ref-003", "绘画分析中的文化因素", "绘画内容受文化背景影响显著...")
            );
        }
        return Collections.emptyList();
    }

    @Override
    public Map<String, Object> executeTool(String toolName, Map<String, Object> params) {
        String idempotencyKey = (String) params.getOrDefault("idempotencyKey", UUID.randomUUID().toString());

        // 幂等检查
        if (savedRecords.containsKey(idempotencyKey)) {
            return savedRecords.get(idempotencyKey);
        }

        Map<String, Object> result = new HashMap<>();
        String recordId = "mock-" + toolName + "-" + UUID.randomUUID().toString().substring(0, 8);

        switch (toolName) {
            case "save_sandbox_record":
                result.put("recordId", recordId);
                result.put("status", "saved");
                result.put("elementCount", params.getOrDefault("elementCount", 0));
                break;
            case "save_htp_record":
                result.put("recordId", recordId);
                result.put("status", "saved");
                break;
            case "get_rag_context":
                result.put("documents", retrieveKnowledge(
                        (String) params.getOrDefault("topic", "sandplay"),
                        (String) params.getOrDefault("query", ""),
                        (int) params.getOrDefault("maxResults", 5)
                ));
                break;
            default:
                throw new ToolExecutionException(toolName, "UNKNOWN_TOOL",
                        "未知工具: " + toolName);
        }

        savedRecords.put(idempotencyKey, result);
        return result;
    }

    @Override
    public void saveAuditRecord(AgentAuditRecord auditRecord) {
        // 本地Mock：打印到stdout，生产环境写入数据库
        System.out.printf("[AUDIT] agent=%s runId=%s latency=%dms error=%s%n",
                auditRecord.getAgentName(),
                auditRecord.getAgentRunId(),
                auditRecord.getLatencyMs(),
                auditRecord.getErrorInfo() != null ? auditRecord.getErrorInfo() : "none");
    }

    @Override
    public String getMode() {
        return "local";
    }

    // ---- 辅助方法 ----

    private void simulateLatency(long ms) {
        try {
            Thread.sleep(Math.min(ms, 200)); // 本地不真实等太久
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }

    private String buildThemeSummary(SandplayAnalysisRequest request) {
        int total = request.getElements() != null ? request.getElements().size() : 0;
        if (total == 0) {
            return "沙盘中没有放置元素。用户通过文字描述表达了自己的状态。";
        }
        return String.format("沙盘中共放置了%d个元素。画面布局呈现一定的结构性特征。"
                + "建议结合用户自己的描述进一步理解作品的含义。", total);
    }

    private String getDominantCategory(SandplayAnalysisRequest request) {
        if (request.getCategoryDistribution() == null || request.getCategoryDistribution().isEmpty()) {
            return "各";
        }
        return request.getCategoryDistribution().entrySet().stream()
                .max(Map.Entry.comparingByValue((a, b) -> Integer.compare(a.getCount(), b.getCount())))
                .map(Map.Entry::getKey)
                .orElse("各");
    }

    private String translateDrawingOrder(String order) {
        if (order == null) return "未提供";
        return switch (order) {
            case "house-first" -> "先画房子";
            case "tree-first" -> "先画树";
            case "person-first" -> "先画人";
            case "not-sure" -> "不确定";
            default -> order;
        };
    }

    private String translateCompleteness(String completeness) {
        if (completeness == null) return "未提供";
        return switch (completeness) {
            case "complete" -> "完整";
            case "mostly-complete" -> "基本完整";
            case "partial" -> "部分完成";
            default -> completeness;
        };
    }
}
