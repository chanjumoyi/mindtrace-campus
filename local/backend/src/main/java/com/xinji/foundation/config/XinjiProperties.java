package com.xinji.foundation.config;

import java.util.ArrayList;
import java.util.List;
import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "xinji")
public class XinjiProperties {
    private final Auth auth = new Auth();
    private final Storage storage = new Storage();
    private final Agent agent = new Agent();
    private final Cors cors = new Cors();
    private final Demo demo = new Demo();

    public Auth getAuth() { return auth; }
    public Storage getStorage() { return storage; }
    public Agent getAgent() { return agent; }
    public Cors getCors() { return cors; }
    public Demo getDemo() { return demo; }

    public static class Auth {
        private long tokenTtlHours = 12;
        public long getTokenTtlHours() { return tokenTtlHours; }
        public void setTokenTtlHours(long tokenTtlHours) { this.tokenTtlHours = tokenTtlHours; }
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
        private int maxAttempts = 3;
        private long retryBackoffMs = 200;
        public String getBaseUrl() { return baseUrl; }
        public void setBaseUrl(String baseUrl) { this.baseUrl = baseUrl; }
        public int getTimeoutMs() { return timeoutMs; }
        public void setTimeoutMs(int timeoutMs) { this.timeoutMs = timeoutMs; }
        public int getMaxAttempts() { return maxAttempts; }
        public void setMaxAttempts(int maxAttempts) { this.maxAttempts = maxAttempts; }
        public long getRetryBackoffMs() { return retryBackoffMs; }
        public void setRetryBackoffMs(long retryBackoffMs) { this.retryBackoffMs = retryBackoffMs; }
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
