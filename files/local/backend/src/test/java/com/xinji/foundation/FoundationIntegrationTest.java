package com.xinji.foundation;

import static org.hamcrest.Matchers.*;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import com.xinji.foundation.ai.AiRateLimitBucketRepository;
import java.io.IOException;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class FoundationIntegrationTest {
    private static HttpServer agent;
    private static int port;
    private static final ConcurrentHashMap<String, AtomicInteger> attempts = new ConcurrentHashMap<>();
    private static final AtomicInteger recoveryAttempts = new AtomicInteger();

    @Autowired MockMvc mvc;
    @Autowired ObjectMapper mapper;
    @Autowired AiRateLimitBucketRepository rateBuckets;

    static {
        try {
            agent = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
            port = agent.getAddress().getPort();
            agent.createContext("/v1/invoke", FoundationIntegrationTest::handleAgent);
            agent.start();
        } catch (IOException e) {
            throw new ExceptionInInitializerError(e);
        }
    }

    @BeforeEach
    void resetRateLimit() {
        rateBuckets.deleteAll();
    }

    @AfterAll
    static void stopAgent() {
        if (agent != null) agent.stop(0);
    }

    @DynamicPropertySource
    static void properties(DynamicPropertyRegistry registry) {
        registry.add("xinji.auth.service-token", () -> "12345678901234567890123456789012");
        registry.add("xinji.agent.base-url", () -> "http://127.0.0.1:" + port);
        registry.add("xinji.agent.timeout-ms", () -> 1000);
        registry.add("xinji.agent.min-timeout-ms", () -> 100);
        registry.add("xinji.agent.connect-timeout-ms", () -> 200);
        registry.add("xinji.agent.per-attempt-timeout-ms", () -> 300);
        registry.add("xinji.agent.max-attempts", () -> 3);
        registry.add("xinji.agent.retry-backoff-ms", () -> 10);
        registry.add("xinji.agent.retry-max-backoff-ms", () -> 20);
        registry.add("xinji.agent.retry-jitter-ms", () -> 0);
        registry.add("xinji.agent.rate-limit-max-requests", () -> 2);
        registry.add("xinji.agent.rate-limit-window-seconds", () -> 60);
        registry.add("xinji.agent.cleanup-interval-ms", () -> 3600000);
    }

    @Test
    void studentCanLoginReadProfileAndUseOwnTaskFlow() throws Exception {
        String token = login("student_demo", "demo123");
        mvc.perform(get("/api/v1/me").header("Authorization", "Bearer " + token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.username").value("student_demo"));

        String body = mvc.perform(post("/api/v1/tasks")
                        .header("Authorization", "Bearer " + token)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"moduleCode\":\"COMMON\",\"taskType\":\"INTEGRATION_TEST\",\"title\":\"测试任务\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.status").value("PENDING"))
                .andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8);
        String id = mapper.readTree(body).path("data").path("id").asText();

        mvc.perform(patch("/api/v1/tasks/{id}/status", id)
                        .header("Authorization", "Bearer " + token)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"status\":\"RUNNING\",\"progress\":30}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.progress").value(30));
    }

    @Test
    void studentCannotReadAuditButAdminCan() throws Exception {
        String student = login("student_demo", "demo123");
        mvc.perform(get("/api/v1/audit-logs").header("Authorization", "Bearer " + student))
                .andExpect(status().isForbidden());

        String admin = login("admin_demo", "admin123");
        mvc.perform(get("/api/v1/audit-logs").header("Authorization", "Bearer " + admin))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.content").isArray());
    }

    @Test
    void aiGatewayRetriesLogsAttemptsAndReplaysIdempotentResult() throws Exception {
        String token = login("student_demo", "demo123");
        String key = "test-idempotency-0001";
        String request = "{\"moduleCode\":\"COMMON\",\"operation\":\"simulate-error\",\"input\":{\"message\":\"hello\"},\"timeoutMs\":1000}";

        String body = mvc.perform(post("/api/v1/ai/invoke")
                        .header("Authorization", "Bearer " + token)
                        .header("Idempotency-Key", key)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(request))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.attempts").value(3))
                .andExpect(jsonPath("$.data.replayed").value(false))
                .andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8);
        String callId = mapper.readTree(body).path("data").path("callId").asText();

        mvc.perform(get("/api/v1/ai/call-logs/{callId}/attempts", callId)
                        .header("Authorization", "Bearer " + token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data", hasSize(3)))
                .andExpect(jsonPath("$.data[0].retryable").value(true))
                .andExpect(jsonPath("$.data[2].status").value("SUCCEEDED"));

        mvc.perform(post("/api/v1/ai/invoke")
                        .header("Authorization", "Bearer " + token)
                        .header("Idempotency-Key", key)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(request))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.replayed").value(true));
    }

    @Test
    void failedIdempotentRequestCanRecoverWithSameKey() throws Exception {
        recoveryAttempts.set(0);
        String token = login("counselor_demo", "demo123");
        String key = "recover-idempotency-0001";
        String request = "{\"moduleCode\":\"COMMON\",\"operation\":\"recover-after-failure\",\"input\":{},\"timeoutMs\":1000}";

        mvc.perform(post("/api/v1/ai/invoke")
                        .header("Authorization", "Bearer " + token)
                        .header("Idempotency-Key", key)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(request))
                .andExpect(status().isBadGateway())
                .andExpect(jsonPath("$.code").value("AGENT_UNAVAILABLE"));

        mvc.perform(post("/api/v1/ai/invoke")
                        .header("Authorization", "Bearer " + token)
                        .header("Idempotency-Key", key)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(request))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.replayed").value(false))
                .andExpect(jsonPath("$.data.attempts").value(1));
    }

    @Test
    void requestSpecificTimeoutIsEnforcedAsHardDeadline() throws Exception {
        String token = login("admin_demo", "admin123");
        long started = System.nanoTime();
        mvc.perform(post("/api/v1/ai/invoke")
                        .header("Authorization", "Bearer " + token)
                        .header("Idempotency-Key", "dynamic-timeout-0001")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"moduleCode\":\"COMMON\",\"operation\":\"timeout\",\"input\":{},\"timeoutMs\":220}"))
                .andExpect(status().isGatewayTimeout())
                .andExpect(jsonPath("$.code").value("AGENT_TIMEOUT"));
        long elapsedMs = (System.nanoTime() - started) / 1_000_000L;
        assertTrue(elapsedMs < 900, "dynamic timeout should finish before the global 1000ms timeout");
    }

    @Test
    void nonRetryableAgentErrorStopsAfterFirstAttempt() throws Exception {
        String token = login("admin_demo", "admin123");
        mvc.perform(post("/api/v1/ai/invoke")
                        .header("Authorization", "Bearer " + token)
                        .header("Idempotency-Key", "non-retryable-0001")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"moduleCode\":\"COMMON\",\"operation\":\"reject\",\"input\":{},\"timeoutMs\":1000}"))
                .andExpect(status().isBadGateway())
                .andExpect(jsonPath("$.code").value("AGENT_REJECTED"));

        mvc.perform(get("/api/v1/ai/call-logs")
                        .header("Authorization", "Bearer " + token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data[0].attempts").value(1));
    }

    @Test
    void rateLimitIsPersistedAndReturnsRetryAfter() throws Exception {
        String token = login("student_demo", "demo123");
        for (int i = 0; i < 2; i++) {
            mvc.perform(post("/api/v1/ai/invoke")
                            .header("Authorization", "Bearer " + token)
                            .header("Idempotency-Key", "rate-limit-key-000" + i)
                            .contentType(MediaType.APPLICATION_JSON)
                            .content("{\"moduleCode\":\"COMMON\",\"operation\":\"echo\",\"input\":{},\"timeoutMs\":1000}"))
                    .andExpect(status().isOk());
        }
        mvc.perform(post("/api/v1/ai/invoke")
                        .header("Authorization", "Bearer " + token)
                        .header("Idempotency-Key", "rate-limit-key-0002")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"moduleCode\":\"COMMON\",\"operation\":\"echo\",\"input\":{},\"timeoutMs\":1000}"))
                .andExpect(status().isTooManyRequests())
                .andExpect(header().exists("Retry-After"))
                .andExpect(jsonPath("$.code").value("RATE_LIMITED"));
    }


    @Test
    void kingdeeServiceTokenHasLeastPrivilegeAndCanInvokeAi() throws Exception {
        String serviceToken = "12345678901234567890123456789012";
        mvc.perform(post("/api/v1/ai/invoke")
                        .header("Authorization", "Bearer " + serviceToken)
                        .header("Idempotency-Key", "service-token-test-0001")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"moduleCode\":\"COMMON\",\"operation\":\"echo\",\"input\":{},\"timeoutMs\":1000}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.status").value("SUCCEEDED"));

        mvc.perform(get("/api/v1/audit-logs")
                        .header("Authorization", "Bearer " + serviceToken))
                .andExpect(status().isForbidden());
    }

    @Test
    void canonicalJsonOrderReplaysAndDifferentBodyConflicts() throws Exception {
        String token = login("student_demo", "demo123");
        String key = "canonical-idempotency-0001";
        String first = "{\"moduleCode\":\"COMMON\",\"operation\":\"echo\",\"input\":{\"a\":1,\"nested\":{\"x\":2,\"y\":3}},\"timeoutMs\":1000}";
        String reordered = "{\"timeoutMs\":1000,\"input\":{\"nested\":{\"y\":3,\"x\":2},\"a\":1},\"operation\":\"echo\",\"moduleCode\":\"COMMON\"}";
        String changed = "{\"moduleCode\":\"COMMON\",\"operation\":\"echo\",\"input\":{\"a\":2},\"timeoutMs\":1000}";

        mvc.perform(post("/api/v1/ai/invoke")
                        .header("Authorization", "Bearer " + token)
                        .header("Idempotency-Key", key)
                        .contentType(MediaType.APPLICATION_JSON).content(first))
                .andExpect(status().isOk()).andExpect(jsonPath("$.data.replayed").value(false));
        mvc.perform(post("/api/v1/ai/invoke")
                        .header("Authorization", "Bearer " + token)
                        .header("Idempotency-Key", key)
                        .contentType(MediaType.APPLICATION_JSON).content(reordered))
                .andExpect(status().isOk()).andExpect(jsonPath("$.data.replayed").value(true));
        mvc.perform(post("/api/v1/ai/invoke")
                        .header("Authorization", "Bearer " + token)
                        .header("Idempotency-Key", key)
                        .contentType(MediaType.APPLICATION_JSON).content(changed))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.code").value("IDEMPOTENCY_CONFLICT"));
    }

    @Test
    void invalidLoginIsRejected() throws Exception {
        mvc.perform(post("/api/v1/auth/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"username\":\"student_demo\",\"password\":\"wrong\"}"))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.code").value("UNAUTHORIZED"));
    }

    private String login(String username, String password) throws Exception {
        String body = mvc.perform(post("/api/v1/auth/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(mapper.writeValueAsString(java.util.Map.of("username", username, "password", password))))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.accessToken", not(blankOrNullString())))
                .andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8);
        JsonNode json = mapper.readTree(body);
        return json.path("data").path("accessToken").asText();
    }

    private static void handleAgent(HttpExchange exchange) throws IOException {
        byte[] requestBytes = exchange.getRequestBody().readAllBytes();
        String request = new String(requestBytes, StandardCharsets.UTF_8);
        String requestId = exchange.getRequestHeaders().getFirst("X-Request-Id");
        if (requestId == null) requestId = Integer.toHexString(request.hashCode());
        int n = attempts.computeIfAbsent(requestId, ignored -> new AtomicInteger()).incrementAndGet();

        if (request.contains("\"operation\":\"simulate-error\"") && n < 3) {
            write(exchange, 503, "{\"code\":\"TRANSIENT\"}");
        } else if (request.contains("\"operation\":\"recover-after-failure\"") && recoveryAttempts.incrementAndGet() <= 3) {
            write(exchange, 503, "{\"code\":\"RECOVERABLE\"}");
        } else if (request.contains("\"operation\":\"reject\"")) {
            write(exchange, 400, "{\"code\":\"INVALID_INPUT\"}");
        } else if (request.contains("\"operation\":\"timeout\"")) {
            try { Thread.sleep(700); } catch (InterruptedException ex) { Thread.currentThread().interrupt(); }
            write(exchange, 200, "{\"status\":\"SUCCEEDED\",\"slow\":true}");
        } else {
            write(exchange, 200, "{\"status\":\"SUCCEEDED\",\"attempt\":" + n + ",\"mock\":true}");
        }
    }

    private static void write(HttpExchange exchange, int status, String body) throws IOException {
        byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
        exchange.getResponseHeaders().set("Content-Type", "application/json");
        exchange.sendResponseHeaders(status, bytes.length);
        try {
            exchange.getResponseBody().write(bytes);
        } catch (IOException ignored) {
            // Dynamic timeout tests may close the client connection before the delayed response is written.
        } finally {
            exchange.close();
        }
    }
}
