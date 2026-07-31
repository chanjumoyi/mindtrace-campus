package com.xinji.foundation;

import static org.hamcrest.Matchers.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.AfterAll;
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

    @Autowired MockMvc mvc;
    @Autowired ObjectMapper mapper;

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

    @AfterAll
    static void stopAgent() {
        if (agent != null) agent.stop(0);
    }

    @DynamicPropertySource
    static void properties(DynamicPropertyRegistry registry) {
        registry.add("xinji.agent.base-url", () -> "http://127.0.0.1:" + port);
        registry.add("xinji.agent.timeout-ms", () -> 1000);
        registry.add("xinji.agent.max-attempts", () -> 3);
        registry.add("xinji.agent.retry-backoff-ms", () -> 5);
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
    void aiGatewayRetriesAndReplaysIdempotentResult() throws Exception {
        String token = login("student_demo", "demo123");
        String key = "test-idempotency-0001";
        String request = "{\"moduleCode\":\"COMMON\",\"operation\":\"simulate-error\",\"input\":{\"message\":\"hello\"},\"timeoutMs\":1000}";

        mvc.perform(post("/api/v1/ai/invoke")
                        .header("Authorization", "Bearer " + token)
                        .header("Idempotency-Key", key)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(request))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.attempts").value(3))
                .andExpect(jsonPath("$.data.replayed").value(false));

        mvc.perform(post("/api/v1/ai/invoke")
                        .header("Authorization", "Bearer " + token)
                        .header("Idempotency-Key", key)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(request))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.replayed").value(true));
    }

    @Test
    void invalidLoginIsRejected() throws Exception {
        mvc.perform(post("/api/v1/auth/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"username\":\"student_demo\",\"password\":\"wrong\"}"))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.code").value("UNAUTHORIZED"));
    }

    @Test
    void multimodalAnalysisRecordFollowsTaskOwnershipAndCanBeDeleted() throws Exception {
        String token = login("student_demo", "demo123");
        String taskBody = mvc.perform(post("/api/v1/tasks")
                        .header("Authorization", "Bearer " + token)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"moduleCode":"MULTIMODAL_AGENT","taskType":"SANDPLAY_ANALYSIS",
                                 "title":"沙盘结构化观察","requestRef":"sandplay:test-record"}
                                """))
                .andExpect(status().isOk())
                .andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8);
        String taskId = mapper.readTree(taskBody).path("data").path("id").asText();

        mvc.perform(post("/api/v1/analysis-records")
                        .header("Authorization", "Bearer " + token)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"moduleType":"SANDPLAY","taskId":"%s","title":"沙盘结构化观察",
                                 "observations":["共有1个元素","中心区域占比100%%"],
                                 "features":{"count":1,"centerRatio":1.0},
                                 "provider":"mock","model":"deterministic-mock","mockResult":true}
                                """.formatted(taskId)))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.code").value("INVALID_STATE_TRANSITION"));

        mvc.perform(patch("/api/v1/tasks/{id}/status", taskId)
                        .header("Authorization", "Bearer " + token)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"status\":\"RUNNING\",\"progress\":10}"))
                .andExpect(status().isOk());

        String recordBody = mvc.perform(post("/api/v1/analysis-records")
                        .header("Authorization", "Bearer " + token)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"moduleType":"SANDPLAY","taskId":"%s","sourceRef":"sandplay:test-record",
                                 "title":"沙盘结构化观察","observations":["共有1个元素","中心区域占比100%%"],
                                 "features":{"count":1,"centerRatio":1.0},
                                 "aiSummary":"本地结构化观察","provider":"mock",
                                 "model":"deterministic-mock","mockResult":true}
                                """.formatted(taskId)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.moduleType").value("SANDPLAY"))
                .andExpect(jsonPath("$.data.observations[0]").value("共有1个元素"))
                .andExpect(jsonPath("$.data.features.count").value(1))
                .andExpect(jsonPath("$.data.mockResult").value(true))
                .andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8);
        String recordId = mapper.readTree(recordBody).path("data").path("id").asText();

        mvc.perform(patch("/api/v1/tasks/{id}/status", taskId)
                        .header("Authorization", "Bearer " + token)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"status\":\"SUCCEEDED\",\"resultRef\":\"" + recordId + "\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.resultRef").value(recordId));

        mvc.perform(get("/api/v1/analysis-records")
                        .param("moduleType", "SANDPLAY")
                        .header("Authorization", "Bearer " + token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data[0].id").value(recordId));

        mvc.perform(delete("/api/v1/analysis-records/{id}", recordId)
                        .header("Authorization", "Bearer " + token))
                .andExpect(status().isOk());
        mvc.perform(get("/api/v1/analysis-records/{id}", recordId)
                        .header("Authorization", "Bearer " + token))
                .andExpect(status().isNotFound());
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
        if (request.contains("simulate-error") && n < 3) {
            write(exchange, 503, "{\"code\":\"TRANSIENT\"}");
        } else {
            write(exchange, 200, "{\"status\":\"SUCCEEDED\",\"attempt\":" + n + ",\"mock\":true}");
        }
    }

    private static void write(HttpExchange exchange, int status, String body) throws IOException {
        byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
        exchange.getResponseHeaders().set("Content-Type", "application/json");
        exchange.sendResponseHeaders(status, bytes.length);
        exchange.getResponseBody().write(bytes);
        exchange.close();
    }
}
