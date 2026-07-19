package com.xinji.foundation.ai;

import jakarta.persistence.*;
import java.time.OffsetDateTime;

@Entity
@Table(name = "ai_call_attempt_log", uniqueConstraints = @UniqueConstraint(name = "uq_ai_attempt_call_no", columnNames = {"call_id", "attempt_no"}))
public class AiCallAttemptLogEntity {
    @Id private String id;
    @Column(name = "call_id", nullable = false) private String callId;
    @Column(name = "attempt_no", nullable = false) private int attemptNo;
    @Column(nullable = false) private String status;
    @Column(name = "latency_ms", nullable = false) private long latencyMs;
    @Column(name = "http_status") private Integer httpStatus;
    @Column(nullable = false) private boolean retryable;
    @Column(name = "backoff_ms", nullable = false) private long backoffMs;
    @Column(name = "error_code") private String errorCode;
    @Column(name = "error_message") private String errorMessage;
    @Column(name = "started_at", nullable = false) private OffsetDateTime startedAt;
    @Column(name = "completed_at", nullable = false) private OffsetDateTime completedAt;

    public String getId() { return id; } public void setId(String id) { this.id = id; }
    public String getCallId() { return callId; } public void setCallId(String callId) { this.callId = callId; }
    public int getAttemptNo() { return attemptNo; } public void setAttemptNo(int attemptNo) { this.attemptNo = attemptNo; }
    public String getStatus() { return status; } public void setStatus(String status) { this.status = status; }
    public long getLatencyMs() { return latencyMs; } public void setLatencyMs(long latencyMs) { this.latencyMs = latencyMs; }
    public Integer getHttpStatus() { return httpStatus; } public void setHttpStatus(Integer httpStatus) { this.httpStatus = httpStatus; }
    public boolean isRetryable() { return retryable; } public void setRetryable(boolean retryable) { this.retryable = retryable; }
    public long getBackoffMs() { return backoffMs; } public void setBackoffMs(long backoffMs) { this.backoffMs = backoffMs; }
    public String getErrorCode() { return errorCode; } public void setErrorCode(String errorCode) { this.errorCode = errorCode; }
    public String getErrorMessage() { return errorMessage; } public void setErrorMessage(String errorMessage) { this.errorMessage = errorMessage; }
    public OffsetDateTime getStartedAt() { return startedAt; } public void setStartedAt(OffsetDateTime startedAt) { this.startedAt = startedAt; }
    public OffsetDateTime getCompletedAt() { return completedAt; } public void setCompletedAt(OffsetDateTime completedAt) { this.completedAt = completedAt; }
}
