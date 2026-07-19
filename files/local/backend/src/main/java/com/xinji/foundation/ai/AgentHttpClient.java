package com.xinji.foundation.ai;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.xinji.foundation.config.XinjiProperties;
import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.time.ZonedDateTime;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletionStage;
import java.util.concurrent.Flow;
import org.springframework.stereotype.Component;

@Component
public class AgentHttpClient {
    private static final TypeReference<Map<String, Object>> MAP_TYPE = new TypeReference<>() {};

    private final HttpClient client;
    private final ObjectMapper mapper;
    private final XinjiProperties properties;
    private final URI invokeUri;

    public AgentHttpClient(HttpClient agentHttpClient, ObjectMapper mapper, XinjiProperties properties) {
        this.client = agentHttpClient;
        this.mapper = mapper;
        this.properties = properties;
        String base = properties.getAgent().getBaseUrl();
        if (base == null || base.isBlank()) throw new IllegalArgumentException("xinji.agent.base-url is required");
        this.invokeUri = URI.create(base.endsWith("/") ? base + "v1/invoke" : base + "/v1/invoke");
        String scheme = invokeUri.getScheme();
        if (!"http".equalsIgnoreCase(scheme) && !"https".equalsIgnoreCase(scheme)) {
            throw new IllegalArgumentException("xinji.agent.base-url must use http or https");
        }
    }

    public TransportResponse invoke(Map<String, Object> outbound, int timeoutMs, String requestId, String idempotencyKey)
            throws IOException, InterruptedException {
        byte[] requestBody = mapper.writeValueAsBytes(outbound);
        HttpRequest request = HttpRequest.newBuilder(invokeUri)
                .timeout(Duration.ofMillis(Math.max(1, timeoutMs)))
                .header("Content-Type", "application/json")
                .header("Accept", "application/json")
                .header("X-Request-Id", requestId)
                .header("Idempotency-Key", idempotencyKey)
                .POST(HttpRequest.BodyPublishers.ofByteArray(requestBody))
                .build();

        HttpResponse<byte[]> response = client.send(request, limitedBodyHandler(properties.getAgent().getMaxResponseBytes()));
        byte[] bytes = response.body() == null ? new byte[0] : response.body();
        String rawBody = new String(bytes, StandardCharsets.UTF_8);
        Map<String, Object> body = Map.of();
        if (response.statusCode() >= 200 && response.statusCode() < 300) {
            if (rawBody.isBlank()) throw new AgentProtocolException("Agent returned an empty success response");
            try {
                body = mapper.readValue(rawBody, MAP_TYPE);
            } catch (IOException ex) {
                throw new AgentProtocolException("Agent returned invalid JSON", ex);
            }
        }
        return new TransportResponse(response.statusCode(), body, safeBody(rawBody), parseRetryAfterMs(response));
    }


    private static HttpResponse.BodyHandler<byte[]> limitedBodyHandler(int limit) {
        return ignored -> new LimitedBodySubscriber(limit);
    }

    private static final class LimitedBodySubscriber implements HttpResponse.BodySubscriber<byte[]> {
        private final HttpResponse.BodySubscriber<byte[]> delegate = HttpResponse.BodySubscribers.ofByteArray();
        private final int limit;
        private Flow.Subscription subscription;
        private int received;
        private boolean terminated;

        private LimitedBodySubscriber(int limit) { this.limit = limit; }
        @Override public CompletionStage<byte[]> getBody() { return delegate.getBody(); }
        @Override public void onSubscribe(Flow.Subscription subscription) {
            this.subscription = subscription;
            delegate.onSubscribe(subscription);
        }
        @Override public void onNext(List<ByteBuffer> items) {
            if (terminated) return;
            long chunk = 0;
            for (ByteBuffer item : items) chunk += item.remaining();
            if ((long) received + chunk > limit) {
                terminated = true;
                subscription.cancel();
                delegate.onError(new AgentProtocolException("Agent response exceeds configured maximum size"));
                return;
            }
            received += (int) chunk;
            delegate.onNext(items);
        }
        @Override public void onError(Throwable throwable) {
            if (terminated) return;
            terminated = true;
            delegate.onError(throwable);
        }
        @Override public void onComplete() {
            if (terminated) return;
            terminated = true;
            delegate.onComplete();
        }
    }

    private static Long parseRetryAfterMs(HttpResponse<?> response) {
        String value = response.headers().firstValue("Retry-After").orElse(null);
        if (value == null || value.isBlank()) return null;
        try {
            long seconds = Long.parseLong(value.trim());
            return Math.max(0, seconds * 1000);
        } catch (NumberFormatException ignored) {
            try {
                ZonedDateTime at = ZonedDateTime.parse(value.trim(), DateTimeFormatter.RFC_1123_DATE_TIME);
                return Math.max(0, Duration.between(ZonedDateTime.now(at.getZone()), at).toMillis());
            } catch (DateTimeParseException ignoredAgain) {
                return null;
            }
        }
    }

    private static String safeBody(String value) {
        if (value == null) return null;
        String sanitized = value.replaceAll("(?i)(token|secret|password|authorization)(\\s*[:=]\\s*)[^,}\\s]+", "$1$2***");
        return sanitized.substring(0, Math.min(500, sanitized.length()));
    }

    public record TransportResponse(int statusCode, Map<String, Object> body, String safeBody, Long retryAfterMs) {}

    public static class AgentProtocolException extends IOException {
        public AgentProtocolException(String message) { super(message); }
        public AgentProtocolException(String message, Throwable cause) { super(message, cause); }
    }
}
