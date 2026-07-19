package com.xinji.foundation.ai;

import jakarta.persistence.*;
import java.time.OffsetDateTime;

@Entity
@Table(name = "ai_rate_limit_bucket", uniqueConstraints = @UniqueConstraint(name = "uq_ai_rate_limit_scope_window", columnNames = {"scope", "window_start"}))
public class AiRateLimitBucketEntity {
    @Id private String id;
    @Column(nullable = false, length = 180) private String scope;
    @Column(name = "window_start", nullable = false) private OffsetDateTime windowStart;
    @Column(name = "request_count", nullable = false) private int requestCount;
    @Column(name = "expires_at", nullable = false) private OffsetDateTime expiresAt;
    @Version @Column(nullable = false) private long version;

    public String getId() { return id; } public void setId(String id) { this.id = id; }
    public String getScope() { return scope; } public void setScope(String scope) { this.scope = scope; }
    public OffsetDateTime getWindowStart() { return windowStart; } public void setWindowStart(OffsetDateTime windowStart) { this.windowStart = windowStart; }
    public int getRequestCount() { return requestCount; } public void setRequestCount(int requestCount) { this.requestCount = requestCount; }
    public OffsetDateTime getExpiresAt() { return expiresAt; } public void setExpiresAt(OffsetDateTime expiresAt) { this.expiresAt = expiresAt; }
    public long getVersion() { return version; } public void setVersion(long version) { this.version = version; }
}
