package com.xinji.kingdee;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.Objects;
import java.util.UUID;

/**
 * 与苍穹 SDK 无关的插件核心。租户实际插件类只负责读取平台上下文、鉴权和调用本类。
 * 这样可避免在仓库里伪造未知版本的苍穹 SDK 类名和 Maven 坐标。
 */
public final class FoundationPluginCore {
    private final URI gatewayBaseUri;
    private final String serviceToken;
    private final HttpClient client;

    public FoundationPluginCore(String gatewayBaseUrl, String serviceToken, Duration timeout) {
        this.gatewayBaseUri = validateBaseUrl(gatewayBaseUrl);
        this.serviceToken = Objects.requireNonNull(serviceToken, "serviceToken");
        this.client = HttpClient.newBuilder().connectTimeout(timeout).build();
    }

    public String invoke(String relativePath, String method, String requestJson, String idempotencyKey, Duration timeout)
            throws IOException, InterruptedException {
        if (relativePath == null || !relativePath.startsWith("/api/v1/")) {
            throw new IllegalArgumentException("Only /api/v1/* gateway paths are allowed");
        }
        URI target = gatewayBaseUri.resolve(relativePath.substring(1));
        HttpRequest.Builder builder = HttpRequest.newBuilder(target)
                .timeout(timeout)
                .header("Authorization", "Bearer " + serviceToken)
                .header("Content-Type", "application/json")
                .header("X-Request-Id", UUID.randomUUID().toString());
        if (idempotencyKey != null && !idempotencyKey.isBlank()) builder.header("Idempotency-Key", idempotencyKey);
        if ("GET".equalsIgnoreCase(method)) builder.GET();
        else if ("DELETE".equalsIgnoreCase(method)) builder.DELETE();
        else builder.method(method.toUpperCase(), HttpRequest.BodyPublishers.ofString(requestJson == null ? "{}" : requestJson));
        HttpResponse<String> response = client.send(builder.build(), HttpResponse.BodyHandlers.ofString());
        if (response.statusCode() < 200 || response.statusCode() >= 300) {
            throw new GatewayException(response.statusCode(), safeBody(response.body()));
        }
        return response.body();
    }

    public String health(Duration timeout) throws IOException, InterruptedException {
        URI target = gatewayBaseUri.resolve("actuator/health");
        HttpRequest request = HttpRequest.newBuilder(target).timeout(timeout).GET().build();
        HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
        if (response.statusCode() != 200) throw new GatewayException(response.statusCode(), safeBody(response.body()));
        return response.body();
    }

    private static URI validateBaseUrl(String value) {
        URI uri = URI.create(Objects.requireNonNull(value, "gatewayBaseUrl"));
        if (!("http".equalsIgnoreCase(uri.getScheme()) || "https".equalsIgnoreCase(uri.getScheme())) || uri.getHost() == null) {
            throw new IllegalArgumentException("gatewayBaseUrl must be an absolute http/https URL");
        }
        String normalized = value.endsWith("/") ? value : value + "/";
        return URI.create(normalized);
    }

    private static String safeBody(String body) {
        if (body == null) return "";
        String redacted = body.replaceAll("(?i)(token|secret|password)(\"?\\s*[:=]\\s*\"?)[^\",}\\s]+", "$1$2***");
        return redacted.substring(0, Math.min(1000, redacted.length()));
    }

    public static final class GatewayException extends IOException {
        private final int statusCode;
        public GatewayException(int statusCode, String message) { super(message); this.statusCode = statusCode; }
        public int statusCode() { return statusCode; }
    }
}
