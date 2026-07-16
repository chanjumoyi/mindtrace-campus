package com.mindline.controller;

import com.mindline.model.*;
import com.mindline.platform.PlatformAdapter;
import com.mindline.sandplay.SandplayGeometryService;
import com.mindline.safety.ContentFilterService;

import java.time.Instant;
import java.util.*;

/**
 * 沙盘分析控制器 —— 编排沙盘分析的完整流程。
 *
 * <p>流程：验证 → 几何特征提取 → Agent分析 → 内容安全检查 → 返回结果
 */
public class SandplayAnalysisController {

    private final SandplayGeometryService geometryService;
    private final PlatformAdapter platformAdapter;
    private final ContentFilterService contentFilter;

    public SandplayAnalysisController(PlatformAdapter platformAdapter) {
        this.geometryService = new SandplayGeometryService();
        this.platformAdapter = platformAdapter;
        this.contentFilter = new ContentFilterService();
    }

    /**
     * 分析沙盘布局。
     *
     * @param elements       沙盘元素列表
     * @param userDescription 用户文字描述
     * @param sessionId      会话ID
     * @return 完整的沙盘分析结果
     */
    public SandplayAnalysisResponse analyze(List<SandplayElement> elements,
                                             String userDescription,
                                             String sessionId) {
        // 1. 安全预检查
        ContentFilterService.SafetyCheckResult safetyCheck =
                contentFilter.safetyPreCheck(userDescription);
        if (safetyCheck.isCrisis()) {
            return buildCrisisResponse(safetyCheck);
        }

        // 2. 几何特征提取
        SandplayAnalysisRequest request = geometryService.extractFeatures(elements);
        request.setSessionId(sessionId);
        request.setUserDescription(userDescription);

        // 3. Agent分析
        SandplayAgentAnalysis agentAnalysis = platformAdapter.analyzeSandplay(request);

        // 4. 内容安全检查
        ContentFilterService.FilterResult filteredTheme =
                contentFilter.filterDiagnosticTerms(agentAnalysis.getThemeSummary());
        agentAnalysis.setThemeSummary(filteredTheme.getFiltered());

        // 5. 构建响应
        SandplayAnalysisResponse response = new SandplayAnalysisResponse();
        response.setAnalysisId("analysis-sand-" + UUID.randomUUID().toString().substring(0, 8));
        response.setGeometricFeatures(buildGeometricFeatures(request));
        response.setAgentAnalysis(agentAnalysis);
        response.setCitations(agentAnalysis.getCitations());
        response.setCreatedAt(Instant.now());

        return response;
    }

    private SandplayAnalysisResponse.GeometricFeatures buildGeometricFeatures(
            SandplayAnalysisRequest request) {
        SandplayAnalysisResponse.GeometricFeatures features =
                new SandplayAnalysisResponse.GeometricFeatures();

        features.setTotalElements(request.getElements() != null
                ? request.getElements().size() : 0);
        features.setCategoryDistribution(request.getCategoryDistribution());
        features.setQuadrantAnalysis(request.getQuadrantAnalysis());
        features.setClusters(request.getClusters());
        features.setAdjacencyEdges(request.getAdjacencyEdges());

        return features;
    }

    private SandplayAnalysisResponse buildCrisisResponse(
            ContentFilterService.SafetyCheckResult safetyCheck) {
        SandplayAnalysisResponse response = new SandplayAnalysisResponse();
        response.setAnalysisId("crisis-" + UUID.randomUUID().toString().substring(0, 8));

        SandplayAgentAnalysis agentAnalysis = new SandplayAgentAnalysis();
        agentAnalysis.setThemeSummary("安全响应已触发。检测到以下关键词："
                + String.join(", ", safetyCheck.getMatchedKeywords()));
        agentAnalysis.setExplorationQuestions(Collections.emptyList());
        agentAnalysis.setDisclaimer(safetyCheck.getSafetyMessage());
        agentAnalysis.setCitations(Collections.emptyList());
        response.setAgentAnalysis(agentAnalysis);

        response.setCreatedAt(Instant.now());
        return response;
    }

    // ---- 响应DTO ----

    public static class SandplayAnalysisResponse {
        private String analysisId;
        private GeometricFeatures geometricFeatures;
        private SandplayAgentAnalysis agentAnalysis;
        private List<Citation> citations;
        private Instant createdAt;

        public String getAnalysisId() { return analysisId; }
        public void setAnalysisId(String analysisId) { this.analysisId = analysisId; }
        public GeometricFeatures getGeometricFeatures() { return geometricFeatures; }
        public void setGeometricFeatures(GeometricFeatures geometricFeatures) { this.geometricFeatures = geometricFeatures; }
        public SandplayAgentAnalysis getAgentAnalysis() { return agentAnalysis; }
        public void setAgentAnalysis(SandplayAgentAnalysis agentAnalysis) { this.agentAnalysis = agentAnalysis; }
        public List<Citation> getCitations() { return citations; }
        public void setCitations(List<Citation> citations) { this.citations = citations; }
        public Instant getCreatedAt() { return createdAt; }
        public void setCreatedAt(Instant createdAt) { this.createdAt = createdAt; }

        public static class GeometricFeatures {
            private int totalElements;
            private Map<String, SandplayAnalysisRequest.CategoryStat> categoryDistribution;
            private SandplayAnalysisRequest.QuadrantAnalysis quadrantAnalysis;
            private List<SandplayAnalysisRequest.ClusterInfo> clusters;
            private List<SandplayAnalysisRequest.AdjacencyEdge> adjacencyEdges;
            public int getTotalElements() { return totalElements; }
            public void setTotalElements(int totalElements) { this.totalElements = totalElements; }
            public Map<String, SandplayAnalysisRequest.CategoryStat> getCategoryDistribution() { return categoryDistribution; }
            public void setCategoryDistribution(Map<String, SandplayAnalysisRequest.CategoryStat> categoryDistribution) { this.categoryDistribution = categoryDistribution; }
            public SandplayAnalysisRequest.QuadrantAnalysis getQuadrantAnalysis() { return quadrantAnalysis; }
            public void setQuadrantAnalysis(SandplayAnalysisRequest.QuadrantAnalysis quadrantAnalysis) { this.quadrantAnalysis = quadrantAnalysis; }
            public List<SandplayAnalysisRequest.ClusterInfo> getClusters() { return clusters; }
            public void setClusters(List<SandplayAnalysisRequest.ClusterInfo> clusters) { this.clusters = clusters; }
            public List<SandplayAnalysisRequest.AdjacencyEdge> getAdjacencyEdges() { return adjacencyEdges; }
            public void setAdjacencyEdges(List<SandplayAnalysisRequest.AdjacencyEdge> adjacencyEdges) { this.adjacencyEdges = adjacencyEdges; }
        }
    }
}
