package com.xinji.kingdee;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URI;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.Arrays;
import java.util.HashSet;
import java.util.Objects;
import java.util.Set;
import java.util.UUID;

/**
 * 苍穹 SDK 无关的 Java 8 网关核心。
 *
 * <p>真实苍穹插件只负责把平台事件和配置映射到本类；鉴权、幂等、重试、限流、日志与审计
 * 仍由 C 的统一网关负责，避免在平台插件中重复实现和泄露密钥。</p>
 */
public final class FoundationPluginCore {
    private static final int DEFAULT_MAX_RESPONSE_BYTES = 1024 * 1024;
    private static final Set<String> ALLOWED_PATH_PREFIXES = new HashSet<String>(Arrays.asList(
            "/api/v1/ai/", "/api/v1/modules", "/api/v1/public/", "/actuator/health"));

    private final URI gatewayBaseUri;
    private final String serviceToken;
    private final int connectTimeoutMs;
    private final int maxResponseBytes;

    public FoundationPluginCore(String gatewayBaseUrl, String serviceToken, Duration connectTimeout) {
        this(gatewayBaseUrl, serviceToken, connectTimeout, DEFAULT_MAX_RESPONSE_BYTES);
    }

    public FoundationPluginCore(String gatewayBaseUrl, String serviceToken, Duration connectTimeout, int maxResponseBytes) {
        this.gatewayBaseUri = validateBaseUrl(gatewayBaseUrl);
        this.serviceToken = requireSecret(serviceToken);
        this.connectTimeoutMs = checkedTimeout(connectTimeout, "connectTimeout");
        if (maxResponseBytes < 1024 || maxResponseBytes > 10 * 1024 * 1024) {
            throw new IllegalArgumentException("maxResponseBytes must be between 1024 and 10485760");
        }
        this.maxResponseBytes = maxResponseBytes;
    }

    public String invoke(String relativePath, String method, String requestJson, String idempotencyKey, Duration timeout)
            throws IOException {
        String normalizedMethod = normalizeMethod(method);
        String normalizedPath = validatePath(relativePath);
        int readTimeoutMs = checkedTimeout(timeout, "timeout");
        URL target = gatewayBaseUri.resolve(normalizedPath.substring(1)).toURL();
        HttpURLConnection connection = (HttpURLConnection) target.openConnection();
        connection.setConnectTimeout(connectTimeoutMs);
        connection.setReadTimeout(readTimeoutMs);
        connection.setRequestMethod(normalizedMethod);
        connection.setRequestProperty("Accept", "application/json");
        connection.setRequestProperty("Authorization", "Bearer " + serviceToken);
        connection.setRequestProperty("X-Request-Id", UUID.randomUUID().toString());
        if (idempotencyKey != null && !idempotencyKey.trim().isEmpty()) {
            connection.setRequestProperty("Idempotency-Key", validateIdempotencyKey(idempotencyKey));
        }
        boolean hasBody = !("GET".equals(normalizedMethod) || "DELETE".equals(normalizedMethod));
        if (hasBody) {
            byte[] body = (requestJson == null ? "{}" : requestJson).getBytes(StandardCharsets.UTF_8);
            connection.setDoOutput(true);
            connection.setRequestProperty("Content-Type", "application/json; charset=UTF-8");
            connection.setFixedLengthStreamingMode(body.length);
            try (OutputStream output = connection.getOutputStream()) {
                output.write(body);
            }
        }

        int status = connection.getResponseCode();
        String responseBody;
        try (InputStream input = status >= 200 && status < 400
                ? connection.getInputStream() : connection.getErrorStream()) {
            responseBody = input == null ? "" : readLimited(input, maxResponseBytes);
        } finally {
            connection.disconnect();
        }
        if (status < 200 || status >= 300) {
            throw new GatewayException(status, safeBody(responseBody));
        }
        return responseBody;
    }

    public String invokeAi(String requestJson, String idempotencyKey, Duration timeout) throws IOException {
        return invoke("/api/v1/ai/invoke", "POST", requestJson, idempotencyKey, timeout);
    }

    public String health(Duration timeout) throws IOException {
        return invoke("/actuator/health", "GET", null, null, timeout);
    }

    private static String validatePath(String value) {
        if (value == null || !value.startsWith("/") || value.contains("..") || value.contains("\\")) {
            throw new IllegalArgumentException("A normalized absolute gateway path is required");
        }
        for (String prefix : ALLOWED_PATH_PREFIXES) {
            if (prefix.endsWith("/")) {
                if (value.startsWith(prefix)) return value;
            } else if (value.equals(prefix) || value.startsWith(prefix + "/") || value.startsWith(prefix + "?")) {
                return value;
            }
        }
        throw new IllegalArgumentException("The gateway path is not allowed: " + value);
    }

    private static String normalizeMethod(String value) {
        String method = Objects.requireNonNull(value, "method").trim().toUpperCase();
        if (!("GET".equals(method) || "POST".equals(method) || "PUT".equals(method)
                || "PATCH".equals(method) || "DELETE".equals(method))) {
            throw new IllegalArgumentException("Unsupported HTTP method: " + value);
        }
        return method;
    }

    private static String validateIdempotencyKey(String value) {
        String normalized = value.trim();
        if (!normalized.matches("[A-Za-z0-9._:-]{8,120}")) {
            throw new IllegalArgumentException("Invalid Idempotency-Key");
        }
        return normalized;
    }

    private static URI validateBaseUrl(String value) {
        URI uri = URI.create(Objects.requireNonNull(value, "gatewayBaseUrl"));
        if (!("http".equalsIgnoreCase(uri.getScheme()) || "https".equalsIgnoreCase(uri.getScheme()))
                || uri.getHost() == null || uri.getUserInfo() != null || uri.getFragment() != null) {
            throw new IllegalArgumentException("gatewayBaseUrl must be an absolute http/https URL without credentials or fragment");
        }
        String normalized = value.endsWith("/") ? value : value + "/";
        return URI.create(normalized);
    }

    private static String requireSecret(String value) {
        String token = Objects.requireNonNull(value, "serviceToken").trim();
        if (token.length() < 32) throw new IllegalArgumentException("serviceToken must contain at least 32 characters");
        return token;
    }

    private static int checkedTimeout(Duration duration, String name) {
        Objects.requireNonNull(duration, name);
        long millis = duration.toMillis();
        if (millis < 1 || millis > Integer.MAX_VALUE) throw new IllegalArgumentException(name + " is out of range");
        return (int) millis;
    }

    private static String readLimited(InputStream input, int limit) throws IOException {
        ByteArrayOutputStream output = new ByteArrayOutputStream(Math.min(limit, 8192));
        byte[] buffer = new byte[8192];
        int total = 0;
        int read;
        while ((read = input.read(buffer)) != -1) {
            total += read;
            if (total > limit) throw new IOException("Gateway response exceeds " + limit + " bytes");
            output.write(buffer, 0, read);
        }
        return new String(output.toByteArray(), StandardCharsets.UTF_8);
    }

    private static String safeBody(String body) {
        if (body == null) return "";
        String redacted = body.replaceAll("(?i)(token|secret|password|authorization)(\\\"?\\s*[:=]\\s*\\\"?)[^\\\",}\\s]+", "$1$2***");
        return redacted.substring(0, Math.min(1000, redacted.length()));
    }

    public static final class GatewayException extends IOException {
        private final int statusCode;
        public GatewayException(int statusCode, String message) {
            super(message == null || message.isEmpty() ? "Gateway returned HTTP " + statusCode : message);
            this.statusCode = statusCode;
        }
        public int statusCode() { return statusCode; }
    }
}
