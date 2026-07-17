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
    @Column(name = "created_at", nullable = false) private OffsetDateTime createdAt;
    @Column(name = "updated_at", nullable = false) private OffsetDateTime updatedAt;
    public String getId() { return id; } public void setId(String id) { this.id = id; }
    public String getScope() { return scope; } public void setScope(String scope) { this.scope = scope; }
    public String getIdempotencyKey() { return idempotencyKey; } public void setIdempotencyKey(String idempotencyKey) { this.idempotencyKey = idempotencyKey; }
    public String getRequestHash() { return requestHash; } public void setRequestHash(String requestHash) { this.requestHash = requestHash; }
    public Integer getResponseStatus() { return responseStatus; } public void setResponseStatus(Integer responseStatus) { this.responseStatus = responseStatus; }
    public String getResponseBody() { return responseBody; } public void setResponseBody(String responseBody) { this.responseBody = responseBody; }
    public String getState() { return state; } public void setState(String state) { this.state = state; }
    public OffsetDateTime getExpiresAt() { return expiresAt; } public void setExpiresAt(OffsetDateTime expiresAt) { this.expiresAt = expiresAt; }
    public OffsetDateTime getCreatedAt() { return createdAt; } public void setCreatedAt(OffsetDateTime createdAt) { this.createdAt = createdAt; }
    public OffsetDateTime getUpdatedAt() { return updatedAt; } public void setUpdatedAt(OffsetDateTime updatedAt) { this.updatedAt = updatedAt; }
}
