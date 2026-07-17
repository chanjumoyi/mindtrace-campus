package com.xinji.foundation.audit;

import jakarta.persistence.*;
import java.time.OffsetDateTime;

@Entity
@Table(name = "audit_log")
public class AuditLogEntity {
    @Id private String id;
    @Column(name = "actor_user_id") private String actorUserId;
    @Column(name = "actor_username") private String actorUsername;
    @Column(nullable = false) private String action;
    @Column(name = "resource_type", nullable = false) private String resourceType;
    @Column(name = "resource_id") private String resourceId;
    @Column(nullable = false) private String result;
    @Column(name = "request_id") private String requestId;
    @Column(name = "ip_address") private String ipAddress;
    @Column(name = "detail_json", columnDefinition = "TEXT") private String detailJson;
    @Column(name = "occurred_at", nullable = false) private OffsetDateTime occurredAt;
    public String getId() { return id; } public void setId(String id) { this.id = id; }
    public String getActorUserId() { return actorUserId; } public void setActorUserId(String actorUserId) { this.actorUserId = actorUserId; }
    public String getActorUsername() { return actorUsername; } public void setActorUsername(String actorUsername) { this.actorUsername = actorUsername; }
    public String getAction() { return action; } public void setAction(String action) { this.action = action; }
    public String getResourceType() { return resourceType; } public void setResourceType(String resourceType) { this.resourceType = resourceType; }
    public String getResourceId() { return resourceId; } public void setResourceId(String resourceId) { this.resourceId = resourceId; }
    public String getResult() { return result; } public void setResult(String result) { this.result = result; }
    public String getRequestId() { return requestId; } public void setRequestId(String requestId) { this.requestId = requestId; }
    public String getIpAddress() { return ipAddress; } public void setIpAddress(String ipAddress) { this.ipAddress = ipAddress; }
    public String getDetailJson() { return detailJson; } public void setDetailJson(String detailJson) { this.detailJson = detailJson; }
    public OffsetDateTime getOccurredAt() { return occurredAt; } public void setOccurredAt(OffsetDateTime occurredAt) { this.occurredAt = occurredAt; }
}
