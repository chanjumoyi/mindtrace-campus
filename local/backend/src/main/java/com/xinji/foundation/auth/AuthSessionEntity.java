package com.xinji.foundation.auth;

import jakarta.persistence.*;
import java.time.OffsetDateTime;

@Entity
@Table(name = "auth_session")
public class AuthSessionEntity {
    @Id private String id;
    @Column(name = "user_id", nullable = false) private String userId;
    @Column(name = "token_hash", nullable = false, unique = true) private String tokenHash;
    @Column(name = "expires_at", nullable = false) private OffsetDateTime expiresAt;
    @Column(name = "revoked_at") private OffsetDateTime revokedAt;
    @Column(name = "created_at", nullable = false) private OffsetDateTime createdAt;
    public String getId() { return id; } public void setId(String id) { this.id = id; }
    public String getUserId() { return userId; } public void setUserId(String userId) { this.userId = userId; }
    public String getTokenHash() { return tokenHash; } public void setTokenHash(String tokenHash) { this.tokenHash = tokenHash; }
    public OffsetDateTime getExpiresAt() { return expiresAt; } public void setExpiresAt(OffsetDateTime expiresAt) { this.expiresAt = expiresAt; }
    public OffsetDateTime getRevokedAt() { return revokedAt; } public void setRevokedAt(OffsetDateTime revokedAt) { this.revokedAt = revokedAt; }
    public OffsetDateTime getCreatedAt() { return createdAt; } public void setCreatedAt(OffsetDateTime createdAt) { this.createdAt = createdAt; }
}
