package com.xinji.foundation.ai;

import jakarta.persistence.*;
import java.time.OffsetDateTime;

@Entity
@Table(name = "idempotency_record", uniqueConstraints = @UniqueConstraint(name = "uq_idempotency_scope_key", columnNames = {"scope", "idempotency_key"}))
public class IdempotencyRecordEntity {
    @Id private String id;
    @Column(nullable = false) private String scope;
    @Column(name = "idempotency_key", nullable = false) private String idempotencyKey;
    @Column(name = "request_hash", nullable = false) private String requestHash;
    @Column(name = "response_status") private Integer responseStatus;
    @Column(name = "response_body", columnDefinition = "TEXT") private String responseBody;
    @Column(nullable = false) private String state;
    @Column(name = "expires_at", nullable = false) private OffsetDateTime expiresAt;
    @Column(name = "lease_until") private OffsetDateTime leaseUntil;
    @Column(name = "source_call_id") private String sourceCallId;
    @Column(name = "last_error_code") private String lastErrorCode;
    @Column(name = "recovery_count", nullable = false) private int recoveryCount;
    @Column(name = "created_at", nullable = false) private OffsetDateTime createdAt;
    @Column(name = "updated_at", nullable = false) private OffsetDateTime updatedAt;
    @Version @Column(nullable = false) private long version;

    public String getId() { return id; } public void setId(String id) { this.id = id; }
    public String getScope() { return scope; } public void setScope(String scope) { this.scope = scope; }
    public String getIdempotencyKey() { return idempotencyKey; } public void setIdempotencyKey(String idempotencyKey) { this.idempotencyKey = idempotencyKey; }
    public String getRequestHash() { return requestHash; } public void setRequestHash(String requestHash) { this.requestHash = requestHash; }
    public Integer getResponseStatus() { return responseStatus; } public void setResponseStatus(Integer responseStatus) { this.responseStatus = responseStatus; }
    public String getResponseBody() { return responseBody; } public void setResponseBody(String responseBody) { this.responseBody = responseBody; }
    public String getState() { return state; } public void setState(String state) { this.state = state; }
    public OffsetDateTime getExpiresAt() { return expiresAt; } public void setExpiresAt(OffsetDateTime expiresAt) { this.expiresAt = expiresAt; }
    public OffsetDateTime getLeaseUntil() { return leaseUntil; } public void setLeaseUntil(OffsetDateTime leaseUntil) { this.leaseUntil = leaseUntil; }
    public String getSourceCallId() { return sourceCallId; } public void setSourceCallId(String sourceCallId) { this.sourceCallId = sourceCallId; }
    public String getLastErrorCode() { return lastErrorCode; } public void setLastErrorCode(String lastErrorCode) { this.lastErrorCode = lastErrorCode; }
    public int getRecoveryCount() { return recoveryCount; } public void setRecoveryCount(int recoveryCount) { this.recoveryCount = recoveryCount; }
    public OffsetDateTime getCreatedAt() { return createdAt; } public void setCreatedAt(OffsetDateTime createdAt) { this.createdAt = createdAt; }
    public OffsetDateTime getUpdatedAt() { return updatedAt; } public void setUpdatedAt(OffsetDateTime updatedAt) { this.updatedAt = updatedAt; }
    public long getVersion() { return version; } public void setVersion(long version) { this.version = version; }
}
