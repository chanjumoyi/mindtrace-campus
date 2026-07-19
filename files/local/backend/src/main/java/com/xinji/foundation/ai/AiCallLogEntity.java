package com.xinji.foundation.ai;

import jakarta.persistence.*;
import java.time.OffsetDateTime;

@Entity
@Table(name = "ai_call_log")
public class AiCallLogEntity {
    @Id private String id;
    @Column(name = "actor_user_id") private String actorUserId;
    @Column(name = "module_code", nullable = false) private String moduleCode;
    @Column(nullable = false) private String operation;
    @Column(name = "provider_mode", nullable = false) private String providerMode;
    @Column(nullable = false) private String status;
    @Column(nullable = false) private int attempts;
    @Column(name = "timeout_ms", nullable = false) private int timeoutMs;
    @Column(name = "latency_ms", nullable = false) private long latencyMs;
    @Column(name = "total_backoff_ms", nullable = false) private long totalBackoffMs;
    @Column(name = "http_status") private Integer httpStatus;
    @Column(nullable = false) private boolean replayed;
    @Column(name = "parent_call_id") private String parentCallId;
    @Column(name = "request_id") private String requestId;
    @Column(name = "idempotency_key") private String idempotencyKey;
    @Column(name = "input_digest") private String inputDigest;
    @Column(name = "output_digest") private String outputDigest;
    @Column(name = "error_code") private String errorCode;
    @Column(name = "error_message") private String errorMessage;
    @Column(name = "started_at", nullable = false) private OffsetDateTime startedAt;
    @Column(name = "completed_at") private OffsetDateTime completedAt;
    @Column(name = "created_at", nullable = false) private OffsetDateTime createdAt;

    public String getId() { return id; } public void setId(String id) { this.id = id; }
    public String getActorUserId() { return actorUserId; } public void setActorUserId(String actorUserId) { this.actorUserId = actorUserId; }
    public String getModuleCode() { return moduleCode; } public void setModuleCode(String moduleCode) { this.moduleCode = moduleCode; }
    public String getOperation() { return operation; } public void setOperation(String operation) { this.operation = operation; }
    public String getProviderMode() { return providerMode; } public void setProviderMode(String providerMode) { this.providerMode = providerMode; }
    public String getStatus() { return status; } public void setStatus(String status) { this.status = status; }
    public int getAttempts() { return attempts; } public void setAttempts(int attempts) { this.attempts = attempts; }
    public int getTimeoutMs() { return timeoutMs; } public void setTimeoutMs(int timeoutMs) { this.timeoutMs = timeoutMs; }
    public long getLatencyMs() { return latencyMs; } public void setLatencyMs(long latencyMs) { this.latencyMs = latencyMs; }
    public long getTotalBackoffMs() { return totalBackoffMs; } public void setTotalBackoffMs(long totalBackoffMs) { this.totalBackoffMs = totalBackoffMs; }
    public Integer getHttpStatus() { return httpStatus; } public void setHttpStatus(Integer httpStatus) { this.httpStatus = httpStatus; }
    public boolean isReplayed() { return replayed; } public void setReplayed(boolean replayed) { this.replayed = replayed; }
    public String getParentCallId() { return parentCallId; } public void setParentCallId(String parentCallId) { this.parentCallId = parentCallId; }
    public String getRequestId() { return requestId; } public void setRequestId(String requestId) { this.requestId = requestId; }
    public String getIdempotencyKey() { return idempotencyKey; } public void setIdempotencyKey(String idempotencyKey) { this.idempotencyKey = idempotencyKey; }
    public String getInputDigest() { return inputDigest; } public void setInputDigest(String inputDigest) { this.inputDigest = inputDigest; }
    public String getOutputDigest() { return outputDigest; } public void setOutputDigest(String outputDigest) { this.outputDigest = outputDigest; }
    public String getErrorCode() { return errorCode; } public void setErrorCode(String errorCode) { this.errorCode = errorCode; }
    public String getErrorMessage() { return errorMessage; } public void setErrorMessage(String errorMessage) { this.errorMessage = errorMessage; }
    public OffsetDateTime getStartedAt() { return startedAt; } public void setStartedAt(OffsetDateTime startedAt) { this.startedAt = startedAt; }
    public OffsetDateTime getCompletedAt() { return completedAt; } public void setCompletedAt(OffsetDateTime completedAt) { this.completedAt = completedAt; }
    public OffsetDateTime getCreatedAt() { return createdAt; } public void setCreatedAt(OffsetDateTime createdAt) { this.createdAt = createdAt; }
}
