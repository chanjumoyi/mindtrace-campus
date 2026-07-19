package com.xinji.foundation.config;

import jakarta.annotation.PostConstruct;
import java.net.URI;
import org.springframework.stereotype.Component;

/** Fail fast instead of running with unsafe or contradictory reliability settings. */
@Component
public class ReliabilityConfigurationValidator {
    private final XinjiProperties properties;

    public ReliabilityConfigurationValidator(XinjiProperties properties) {
        this.properties = properties;
    }

    @PostConstruct
    void validate() {
        XinjiProperties.Auth auth = properties.getAuth();
        if (auth.getServiceToken() != null && !auth.getServiceToken().isBlank() && auth.getServiceToken().length() < 32) {
            throw new IllegalStateException("APP_SERVICE_TOKEN must contain at least 32 characters when configured");
        }
        if (auth.getServiceAccountId() == null || auth.getServiceAccountId().isBlank()
                || auth.getServiceAccountUsername() == null || auth.getServiceAccountUsername().isBlank()) {
            throw new IllegalStateException("Kingdee service account id and username must not be blank");
        }
        if (auth.getServicePermissions() == null || auth.getServicePermissions().isEmpty()) {
            throw new IllegalStateException("APP_SERVICE_PERMISSIONS must not be empty when using the Kingdee service token");
        }

        XinjiProperties.Agent agent = properties.getAgent();
        validateBaseUrl(agent.getBaseUrl());
        positive(agent.getTimeoutMs(), "APP_AGENT_TIMEOUT_MS");
        positive(agent.getMinTimeoutMs(), "APP_AGENT_MIN_TIMEOUT_MS");
        positive(agent.getConnectTimeoutMs(), "APP_AGENT_CONNECT_TIMEOUT_MS");
        positive(agent.getPerAttemptTimeoutMs(), "APP_AGENT_PER_ATTEMPT_TIMEOUT_MS");
        positive(agent.getMaxAttempts(), "APP_AGENT_MAX_ATTEMPTS");
        positive(agent.getRateLimitWindowSeconds(), "APP_AGENT_RATE_LIMIT_WINDOW_SECONDS");
        positive(agent.getIdempotencyTtlHours(), "APP_AGENT_IDEMPOTENCY_TTL_HOURS");
        positive(agent.getCleanupIntervalMs(), "APP_AGENT_CLEANUP_INTERVAL_MS");
        positive(agent.getMaxResponseBytes(), "APP_AGENT_MAX_RESPONSE_BYTES");
        nonNegative(agent.getRetryBackoffMs(), "APP_AGENT_RETRY_BACKOFF_MS");
        nonNegative(agent.getRetryMaxBackoffMs(), "APP_AGENT_RETRY_MAX_BACKOFF_MS");
        nonNegative(agent.getRetryJitterMs(), "APP_AGENT_RETRY_JITTER_MS");
        nonNegative(agent.getRateLimitMaxRequests(), "APP_AGENT_RATE_LIMIT_MAX_REQUESTS");
        nonNegative(agent.getIdempotencyLeaseGraceMs(), "APP_AGENT_IDEMPOTENCY_LEASE_GRACE_MS");
        if (agent.getMinTimeoutMs() > agent.getTimeoutMs()) {
            throw new IllegalStateException("APP_AGENT_MIN_TIMEOUT_MS must not exceed APP_AGENT_TIMEOUT_MS");
        }
        if (agent.getRetryBackoffMs() > agent.getRetryMaxBackoffMs()) {
            throw new IllegalStateException("APP_AGENT_RETRY_BACKOFF_MS must not exceed APP_AGENT_RETRY_MAX_BACKOFF_MS");
        }
        if (agent.getMaxAttempts() > 10) {
            throw new IllegalStateException("APP_AGENT_MAX_ATTEMPTS must not exceed 10");
        }
        if (agent.getTimeoutMs() > 120000 || agent.getPerAttemptTimeoutMs() > 120000
                || agent.getConnectTimeoutMs() > 120000) {
            throw new IllegalStateException("Agent timeout settings must not exceed 120000 ms");
        }
        if (agent.getRateLimitWindowSeconds() > 86400) {
            throw new IllegalStateException("APP_AGENT_RATE_LIMIT_WINDOW_SECONDS must not exceed 86400");
        }
        if (agent.getMaxResponseBytes() > 10 * 1024 * 1024) {
            throw new IllegalStateException("APP_AGENT_MAX_RESPONSE_BYTES must not exceed 10 MiB");
        }
    }

    private static void validateBaseUrl(String value) {
        try {
            URI uri = URI.create(value == null ? "" : value.trim());
            if (!("http".equalsIgnoreCase(uri.getScheme()) || "https".equalsIgnoreCase(uri.getScheme()))
                    || uri.getHost() == null || uri.getUserInfo() != null || uri.getFragment() != null) {
                throw new IllegalStateException("APP_AGENT_BASE_URL must be an absolute http/https URL without credentials or fragment");
            }
        } catch (IllegalArgumentException ex) {
            throw new IllegalStateException("APP_AGENT_BASE_URL is invalid", ex);
        }
    }

    private static void positive(long value, String name) {
        if (value <= 0) throw new IllegalStateException(name + " must be greater than zero");
    }

    private static void nonNegative(long value, String name) {
        if (value < 0) throw new IllegalStateException(name + " must not be negative");
    }
}
