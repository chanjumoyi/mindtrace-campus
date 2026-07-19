package com.xinji.foundation.config;

import java.util.ArrayList;
import java.util.List;
import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "xinji")
public class XinjiProperties {
    private final Auth auth = new Auth();
    private final Storage storage = new Storage();
    private final Agent agent = new Agent();
    private final Handwriting handwriting = new Handwriting();
    private final Cors cors = new Cors();
    private final Demo demo = new Demo();

    public Auth getAuth() { return auth; }
    public Storage getStorage() { return storage; }
    public Agent getAgent() { return agent; }
    public Handwriting getHandwriting() { return handwriting; }
    public Cors getCors() { return cors; }
    public Demo getDemo() { return demo; }

    public static class Auth {
        private long tokenTtlHours = 12;
        private String serviceToken = "";
        private String serviceAccountId = "kingdee-service";
        private String serviceAccountUsername = "kingdee_service";
        private String serviceAccountDisplayName = "苍穹集成服务";
        private List<String> servicePermissions = new ArrayList<>(List.of("ai:invoke", "ai:log:read", "module:read"));
        public long getTokenTtlHours() { return tokenTtlHours; }
        public void setTokenTtlHours(long tokenTtlHours) { this.tokenTtlHours = tokenTtlHours; }
        public String getServiceToken() { return serviceToken; }
        public void setServiceToken(String serviceToken) { this.serviceToken = serviceToken; }
        public String getServiceAccountId() { return serviceAccountId; }
        public void setServiceAccountId(String serviceAccountId) { this.serviceAccountId = serviceAccountId; }
        public String getServiceAccountUsername() { return serviceAccountUsername; }
        public void setServiceAccountUsername(String serviceAccountUsername) { this.serviceAccountUsername = serviceAccountUsername; }
        public String getServiceAccountDisplayName() { return serviceAccountDisplayName; }
        public void setServiceAccountDisplayName(String serviceAccountDisplayName) { this.serviceAccountDisplayName = serviceAccountDisplayName; }
        public List<String> getServicePermissions() { return servicePermissions; }
        public void setServicePermissions(List<String> servicePermissions) { this.servicePermissions = servicePermissions == null ? new ArrayList<>() : new ArrayList<>(servicePermissions); }
    }

    public static class Storage {
        private String root = "./storage";
        private List<String> allowedContentTypes = new ArrayList<>();
        public String getRoot() { return root; }
        public void setRoot(String root) { this.root = root; }
        public List<String> getAllowedContentTypes() { return allowedContentTypes; }
        public void setAllowedContentTypes(List<String> allowedContentTypes) { this.allowedContentTypes = allowedContentTypes; }
    }

    public static class Agent {
        private String baseUrl = "http://localhost:8090";
        private int timeoutMs = 5000;
        private int minTimeoutMs = 200;
        private int connectTimeoutMs = 1500;
        private int perAttemptTimeoutMs = 2500;
        private int maxAttempts = 3;
        private long retryBackoffMs = 200;
        private long retryMaxBackoffMs = 1500;
        private long retryJitterMs = 100;
        private int rateLimitMaxRequests = 60;
        private int rateLimitWindowSeconds = 60;
        private long idempotencyTtlHours = 24;
        private long idempotencyLeaseGraceMs = 3000;
        private long cleanupIntervalMs = 300000;
        private int maxResponseBytes = 2097152;

        public String getBaseUrl() { return baseUrl; }
        public void setBaseUrl(String baseUrl) { this.baseUrl = baseUrl; }
        public int getTimeoutMs() { return timeoutMs; }
        public void setTimeoutMs(int timeoutMs) { this.timeoutMs = timeoutMs; }
        public int getMinTimeoutMs() { return minTimeoutMs; }
        public void setMinTimeoutMs(int minTimeoutMs) { this.minTimeoutMs = minTimeoutMs; }
        public int getConnectTimeoutMs() { return connectTimeoutMs; }
        public void setConnectTimeoutMs(int connectTimeoutMs) { this.connectTimeoutMs = connectTimeoutMs; }
        public int getPerAttemptTimeoutMs() { return perAttemptTimeoutMs; }
        public void setPerAttemptTimeoutMs(int perAttemptTimeoutMs) { this.perAttemptTimeoutMs = perAttemptTimeoutMs; }
        public int getMaxAttempts() { return maxAttempts; }
        public void setMaxAttempts(int maxAttempts) { this.maxAttempts = maxAttempts; }
        public long getRetryBackoffMs() { return retryBackoffMs; }
        public void setRetryBackoffMs(long retryBackoffMs) { this.retryBackoffMs = retryBackoffMs; }
        public long getRetryMaxBackoffMs() { return retryMaxBackoffMs; }
        public void setRetryMaxBackoffMs(long retryMaxBackoffMs) { this.retryMaxBackoffMs = retryMaxBackoffMs; }
        public long getRetryJitterMs() { return retryJitterMs; }
        public void setRetryJitterMs(long retryJitterMs) { this.retryJitterMs = retryJitterMs; }
        public int getRateLimitMaxRequests() { return rateLimitMaxRequests; }
        public void setRateLimitMaxRequests(int rateLimitMaxRequests) { this.rateLimitMaxRequests = rateLimitMaxRequests; }
        public int getRateLimitWindowSeconds() { return rateLimitWindowSeconds; }
        public void setRateLimitWindowSeconds(int rateLimitWindowSeconds) { this.rateLimitWindowSeconds = rateLimitWindowSeconds; }
        public long getIdempotencyTtlHours() { return idempotencyTtlHours; }
        public void setIdempotencyTtlHours(long idempotencyTtlHours) { this.idempotencyTtlHours = idempotencyTtlHours; }
        public long getIdempotencyLeaseGraceMs() { return idempotencyLeaseGraceMs; }
        public void setIdempotencyLeaseGraceMs(long idempotencyLeaseGraceMs) { this.idempotencyLeaseGraceMs = idempotencyLeaseGraceMs; }
        public long getCleanupIntervalMs() { return cleanupIntervalMs; }
        public void setCleanupIntervalMs(long cleanupIntervalMs) { this.cleanupIntervalMs = cleanupIntervalMs; }
        public int getMaxResponseBytes() { return maxResponseBytes; }
        public void setMaxResponseBytes(int maxResponseBytes) { this.maxResponseBytes = maxResponseBytes; }
    }

    public static class Handwriting {
        private String baseUrl = "http://localhost:8091";
        private int timeoutMs = 30000;
        public String getBaseUrl() { return baseUrl; }
        public void setBaseUrl(String baseUrl) { this.baseUrl = baseUrl; }
        public int getTimeoutMs() { return timeoutMs; }
        public void setTimeoutMs(int timeoutMs) { this.timeoutMs = timeoutMs; }
    }

    public static class Cors {
        private List<String> allowedOrigins = new ArrayList<>();
        public List<String> getAllowedOrigins() { return allowedOrigins; }
        public void setAllowedOrigins(List<String> allowedOrigins) { this.allowedOrigins = allowedOrigins; }
    }

    public static class Demo {
        private boolean enabled = true;
        private String studentPassword = "demo123";
        private String counselorPassword = "demo123";
        private String adminPassword = "admin123";
        public boolean isEnabled() { return enabled; }
        public void setEnabled(boolean enabled) { this.enabled = enabled; }
        public String getStudentPassword() { return studentPassword; }
        public void setStudentPassword(String studentPassword) { this.studentPassword = studentPassword; }
        public String getCounselorPassword() { return counselorPassword; }
        public void setCounselorPassword(String counselorPassword) { this.counselorPassword = counselorPassword; }
        public String getAdminPassword() { return adminPassword; }
        public void setAdminPassword(String adminPassword) { this.adminPassword = adminPassword; }
    }
}
