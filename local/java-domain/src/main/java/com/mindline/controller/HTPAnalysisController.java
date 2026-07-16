package com.mindline.controller;

import com.mindline.htp.HTPObservationService;
import com.mindline.model.*;
import com.mindline.platform.PlatformAdapter;
import com.mindline.safety.ContentFilterService;

import java.time.Instant;
import java.util.*;

/**
 * 房树人分析控制器 —— 编排HTP分析的完整流程（含多模态降级）。
 */
public class HTPAnalysisController {

    private final HTPObservationService observationService;
    private final PlatformAdapter platformAdapter;
    private final ContentFilterService contentFilter;

    public HTPAnalysisController(PlatformAdapter platformAdapter) {
        this.observationService = new HTPObservationService(platformAdapter);
        this.platformAdapter = platformAdapter;
        this.contentFilter = new ContentFilterService();
    }

    public HTPAnalysisResponse analyze(HTPAnalysisRequest request) {
        // 1. 安全预检查
        String fullUserText = buildUserText(request);
        ContentFilterService.SafetyCheckResult safetyCheck =
                contentFilter.safetyPreCheck(fullUserText);
        if (safetyCheck.isCrisis()) {
            return buildCrisisResponse(safetyCheck);
        }

        // 2. 视觉观察（含降级）
        String degradationNote = null;
        VisualObservation visualObs = observationService.getVisualObservation(request.getImageRef());
        if (visualObs == null && request.getImageRef() != null && !request.getImageRef().isEmpty()) {
            degradationNote = "图像分析暂不可用，以下分析仅基于问卷信息";
        }
        request.setVisualObservation(visualObs);

        // 3. Agent分析
        HTPAgentAnalysis agentAnalysis = platformAdapter.analyzeHTP(request);

        // 4. 内容安全检查
        ContentFilterService.FilterResult filteredObs =
                contentFilter.filterDiagnosticTerms(agentAnalysis.getObservations());
        agentAnalysis.setObservations(filteredObs.getFiltered());

        // 5. 构建响应
        HTPAnalysisResponse response = new HTPAnalysisResponse();
        response.setAnalysisId("analysis-htp-" + UUID.randomUUID().toString().substring(0, 8));
        response.setVisualObservation(visualObs);
        response.setQuestionnaireSummary(buildQuestionnaireSummary(request));
        response.setAgentAnalysis(agentAnalysis);
        response.setCitations(agentAnalysis.getCitations());
        response.setDegradationNote(degradationNote);
        response.setCreatedAt(Instant.now());

        return response;
    }

    private String buildUserText(HTPAnalysisRequest req) {
        StringBuilder sb = new StringBuilder();
        if (req.getHouseDescription() != null) sb.append(req.getHouseDescription()).append(" ");
        if (req.getTreeDescription() != null) sb.append(req.getTreeDescription()).append(" ");
        if (req.getPersonDescription() != null) sb.append(req.getPersonDescription());
        return sb.toString().trim();
    }

    private HTPAnalysisResponse.HTPQuestionnaireSummary buildQuestionnaireSummary(HTPAnalysisRequest req) {
        HTPAnalysisResponse.HTPQuestionnaireSummary summary =
                new HTPAnalysisResponse.HTPQuestionnaireSummary();
        summary.setDrawingOrder(req.getDrawingOrder());
        summary.setCompleteness(req.getCompleteness());
        summary.setHouseDescriptionProvided(req.getHouseDescription() != null && !req.getHouseDescription().isEmpty());
        summary.setTreeDescriptionProvided(req.getTreeDescription() != null && !req.getTreeDescription().isEmpty());
        summary.setPersonDescriptionProvided(req.getPersonDescription() != null && !req.getPersonDescription().isEmpty());
        return summary;
    }

    private HTPAnalysisResponse buildCrisisResponse(ContentFilterService.SafetyCheckResult safetyCheck) {
        HTPAnalysisResponse response = new HTPAnalysisResponse();
        response.setAnalysisId("crisis-htp-" + UUID.randomUUID().toString().substring(0, 8));

        HTPAgentAnalysis agentAnalysis = new HTPAgentAnalysis();
        agentAnalysis.setObservations("安全响应已触发。检测到以下关键词："
                + String.join(", ", safetyCheck.getMatchedKeywords()));
        agentAnalysis.setUserInterpretation("");
        agentAnalysis.setExplorationPrompts(Collections.emptyList());
        agentAnalysis.setDisclaimer(safetyCheck.getSafetyMessage());
        response.setAgentAnalysis(agentAnalysis);
        response.setCreatedAt(Instant.now());

        return response;
    }

    // ---- 响应DTO ----

    public static class HTPAnalysisResponse {
        private String analysisId;
        private VisualObservation visualObservation;
        private HTPQuestionnaireSummary questionnaireSummary;
        private HTPAgentAnalysis agentAnalysis;
        private List<Citation> citations;
        private String degradationNote;
        private Instant createdAt;

        public String getAnalysisId() { return analysisId; }
        public void setAnalysisId(String analysisId) { this.analysisId = analysisId; }
        public VisualObservation getVisualObservation() { return visualObservation; }
        public void setVisualObservation(VisualObservation visualObservation) { this.visualObservation = visualObservation; }
        public HTPQuestionnaireSummary getQuestionnaireSummary() { return questionnaireSummary; }
        public void setQuestionnaireSummary(HTPQuestionnaireSummary questionnaireSummary) { this.questionnaireSummary = questionnaireSummary; }
        public HTPAgentAnalysis getAgentAnalysis() { return agentAnalysis; }
        public void setAgentAnalysis(HTPAgentAnalysis agentAnalysis) { this.agentAnalysis = agentAnalysis; }
        public List<Citation> getCitations() { return citations; }
        public void setCitations(List<Citation> citations) { this.citations = citations; }
        public String getDegradationNote() { return degradationNote; }
        public void setDegradationNote(String degradationNote) { this.degradationNote = degradationNote; }
        public Instant getCreatedAt() { return createdAt; }
        public void setCreatedAt(Instant createdAt) { this.createdAt = createdAt; }

        public static class HTPQuestionnaireSummary {
            private String drawingOrder;
            private String completeness;
            private boolean houseDescriptionProvided;
            private boolean treeDescriptionProvided;
            private boolean personDescriptionProvided;
            public String getDrawingOrder() { return drawingOrder; }
            public void setDrawingOrder(String drawingOrder) { this.drawingOrder = drawingOrder; }
            public String getCompleteness() { return completeness; }
            public void setCompleteness(String completeness) { this.completeness = completeness; }
            public boolean isHouseDescriptionProvided() { return houseDescriptionProvided; }
            public void setHouseDescriptionProvided(boolean houseDescriptionProvided) { this.houseDescriptionProvided = houseDescriptionProvided; }
            public boolean isTreeDescriptionProvided() { return treeDescriptionProvided; }
            public void setTreeDescriptionProvided(boolean treeDescriptionProvided) { this.treeDescriptionProvided = treeDescriptionProvided; }
            public boolean isPersonDescriptionProvided() { return personDescriptionProvided; }
            public void setPersonDescriptionProvided(boolean personDescriptionProvided) { this.personDescriptionProvided = personDescriptionProvided; }
        }
    }
}
