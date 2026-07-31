package com.xinji.foundation.analysis;

import jakarta.persistence.*;
import java.time.OffsetDateTime;

@Entity
@Table(name = "multimodal_analysis_record")
public class MultimodalAnalysisRecordEntity {
    @Id private String id;
    @Column(name = "owner_user_id", nullable = false) private String ownerUserId;
    @Enumerated(EnumType.STRING)
    @Column(name = "module_type", nullable = false) private AnalysisModuleType moduleType;
    @Column(name = "task_id", nullable = false, unique = true) private String taskId;
    @Column(name = "source_ref") private String sourceRef;
    @Column(nullable = false) private String title;
    @Column(name = "observation_json", nullable = false, columnDefinition = "TEXT") private String observationJson;
    @Column(name = "ai_summary", columnDefinition = "TEXT") private String aiSummary;
    @Column private String provider;
    @Column private String model;
    @Column(name = "mock_result", nullable = false) private boolean mockResult;
    @Column(name = "created_at", nullable = false) private OffsetDateTime createdAt;
    @Column(name = "deleted_at") private OffsetDateTime deletedAt;

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }
    public String getOwnerUserId() { return ownerUserId; }
    public void setOwnerUserId(String ownerUserId) { this.ownerUserId = ownerUserId; }
    public AnalysisModuleType getModuleType() { return moduleType; }
    public void setModuleType(AnalysisModuleType moduleType) { this.moduleType = moduleType; }
    public String getTaskId() { return taskId; }
    public void setTaskId(String taskId) { this.taskId = taskId; }
    public String getSourceRef() { return sourceRef; }
    public void setSourceRef(String sourceRef) { this.sourceRef = sourceRef; }
    public String getTitle() { return title; }
    public void setTitle(String title) { this.title = title; }
    public String getObservationJson() { return observationJson; }
    public void setObservationJson(String observationJson) { this.observationJson = observationJson; }
    public String getAiSummary() { return aiSummary; }
    public void setAiSummary(String aiSummary) { this.aiSummary = aiSummary; }
    public String getProvider() { return provider; }
    public void setProvider(String provider) { this.provider = provider; }
    public String getModel() { return model; }
    public void setModel(String model) { this.model = model; }
    public boolean isMockResult() { return mockResult; }
    public void setMockResult(boolean mockResult) { this.mockResult = mockResult; }
    public OffsetDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(OffsetDateTime createdAt) { this.createdAt = createdAt; }
    public OffsetDateTime getDeletedAt() { return deletedAt; }
    public void setDeletedAt(OffsetDateTime deletedAt) { this.deletedAt = deletedAt; }
}
