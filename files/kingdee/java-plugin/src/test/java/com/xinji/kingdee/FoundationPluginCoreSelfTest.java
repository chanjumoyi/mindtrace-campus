package com.xinji.kingdee;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.time.Duration;

public final class FoundationPluginCoreSelfTest {
    public static void main(String[] args) throws Exception {
        HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/actuator/health", exchange -> respond(exchange, 200, "{\"status\":\"UP\"}"));
        server.createContext("/api/v1/ai/invoke", exchange -> {
            assertEquals("Bearer 12345678901234567890123456789012", exchange.getRequestHeaders().getFirst("Authorization"));
            assertEquals("core-test-0001", exchange.getRequestHeaders().getFirst("Idempotency-Key"));
            respond(exchange, 200, "{\"code\":\"OK\"}");
        });
        server.start();
        try {
            String base = "http://127.0.0.1:" + server.getAddress().getPort();
            FoundationPluginCore core = new FoundationPluginCore(base, "12345678901234567890123456789012", Duration.ofSeconds(1));
            assertEquals("{\"status\":\"UP\"}", core.health(Duration.ofSeconds(1)));
            assertEquals("{\"code\":\"OK\"}", core.invokeAi("{}", "core-test-0001", Duration.ofSeconds(1)));
            assertRejected(core, "/api/v1/audit");
            assertRejected(core, "/api/v1/modulesevil");
            assertRejected(core, "/actuator/healthcheck");
            System.out.println("FoundationPluginCoreSelfTest: PASS");
        } finally {
            server.stop(0);
        }
    }

    private static void assertRejected(FoundationPluginCore core, String path) throws Exception {
        try {
            core.invoke(path, "GET", null, null, Duration.ofSeconds(1));
            throw new AssertionError("Forbidden path was accepted: " + path);
        } catch (IllegalArgumentException expected) { }
    }

    private static void respond(HttpExchange exchange, int status, String body) throws IOException {
        byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
        exchange.getResponseHeaders().set("Content-Type", "application/json");
        exchange.sendResponseHeaders(status, bytes.length);
        exchange.getResponseBody().write(bytes);
        exchange.close();
    }

    private static void assertEquals(String expected, String actual) {
        if (!expected.equals(actual)) throw new AssertionError("expected=" + expected + ", actual=" + actual);
    }
}
