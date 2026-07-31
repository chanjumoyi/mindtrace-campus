package com.xinji.foundation.safety;

import jakarta.persistence.*;
import java.time.OffsetDateTime;

@Entity
@Table(name = "risk_signals")
public class RiskSignalEntity {
    @Id private String id;
    @Column(name = "user_id", nullable = false) private String userId;
    @Column(nullable = false, length = 10) private String level;
    @Column(nullable = false, length = 20) private String source;
    @Column(name = "trigger_content", nullable = false, columnDefinition = "TEXT") private String triggerContent;
    @Column(name = "created_at", nullable = false) private OffsetDateTime createdAt;

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }
    public String getUserId() { return userId; }
    public void setUserId(String userId) { this.userId = userId; }
    public String getLevel() { return level; }
    public void setLevel(String level) { this.level = level; }
    public String getSource() { return source; }
    public void setSource(String source) { this.source = source; }
    public String getTriggerContent() { return triggerContent; }
    public void setTriggerContent(String triggerContent) { this.triggerContent = triggerContent; }
    public OffsetDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(OffsetDateTime createdAt) { this.createdAt = createdAt; }
}
