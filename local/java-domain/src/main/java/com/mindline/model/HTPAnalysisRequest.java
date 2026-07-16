package com.mindline.model;

import java.util.List;

/**
 * 房树人分析请求 —— 包含视觉观察和问卷数据，用于Agent分析。
 */
public class HTPAnalysisRequest {

    private String sessionId;
    private String imageRef;
    private String drawingOrder;
    private String completeness;
    private String houseDescription;
    private String treeDescription;
    private String personDescription;

    // 多模态模型视觉观察（可为null，表示降级模式）
    private VisualObservation visualObservation;

    public HTPAnalysisRequest() {}

    public String getSessionId() { return sessionId; }
    public void setSessionId(String sessionId) { this.sessionId = sessionId; }

    public String getImageRef() { return imageRef; }
    public void setImageRef(String imageRef) { this.imageRef = imageRef; }

    public String getDrawingOrder() { return drawingOrder; }
    public void setDrawingOrder(String drawingOrder) { this.drawingOrder = drawingOrder; }

    public String getCompleteness() { return completeness; }
    public void setCompleteness(String completeness) { this.completeness = completeness; }

    public String getHouseDescription() { return houseDescription; }
    public void setHouseDescription(String houseDescription) { this.houseDescription = houseDescription; }

    public String getTreeDescription() { return treeDescription; }
    public void setTreeDescription(String treeDescription) { this.treeDescription = treeDescription; }

    public String getPersonDescription() { return personDescription; }
    public void setPersonDescription(String personDescription) { this.personDescription = personDescription; }

    public VisualObservation getVisualObservation() { return visualObservation; }
    public void setVisualObservation(VisualObservation visualObservation) { this.visualObservation = visualObservation; }
}
