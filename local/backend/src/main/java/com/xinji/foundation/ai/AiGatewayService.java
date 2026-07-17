package com.xinji.foundation.ai;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.xinji.foundation.audit.AuditService;
import com.xinji.foundation.auth.SecurityUtils;
import com.xinji.foundation.common.*;
import com.xinji.foundation.config.XinjiProperties;
import java.time.OffsetDateTime;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

@Service
public class AiGatewayService {
    private final RestClient client;
    private final XinjiProperties properties;
    private final IdempotencyRecordRepository idempotencyRepository;
    private final AiCallLogRepository logs;
    private final ObjectMapper mapper;
    private final Jsons jsons;
    private final AuditService audit;
    private final SimpleRateLimiter rateLimiter;

    public AiGatewayService(RestClient agentRestClient, XinjiProperties properties, IdempotencyRecordRepository idempotencyRepository, AiCallLogRepository logs, ObjectMapper mapper, Jsons jsons, AuditService audit, SimpleRateLimiter rateLimiter) {
        this.client = agentRestClient; this.properties = properties; this.idempotencyRepository = idempotencyRepository; this.logs = logs; this.mapper = mapper; this.jsons = jsons; this.audit = audit; this.rateLimiter = rateLimiter;
    }

    public InvokeResponse invoke(String idempotencyKey, InvokeRequest request) {
        var actor = SecurityUtils.current();
        rateLimiter.check(actor.id(), 60);
        String key = validateKey(idempotencyKey);
        String module = normalizeCode(request.moduleCode());
        String operation = normalizeOperation(request.operation());
        int timeout = request.timeoutMs() == null ? properties.getAgent().getTimeoutMs() : Math.max(500, Math.min(request.timeoutMs(), properties.getAgent().getTimeoutMs()));
        String scope = "AI_INVOKE:" + actor.id();
        String requestJson = jsons.write(new InvokeRequest(module, operation, request.input(), timeout));
        String requestHash = Hashes.sha256(requestJson);

        var existing = idempotencyRepository.findByScopeAndIdempotencyKey(scope, key);
        if (existing.isPresent()) {
            IdempotencyRecordEntity record = existing.get();
            if (!record.getRequestHash().equals(requestHash)) throw new BusinessException(ErrorCode.IDEMPOTENCY_CONFLICT, "相同 Idempotency-Key 对应了不同请求");
            if ("COMPLETED".equals(record.getState()) && record.getResponseBody() != null) {
                try { return mapper.readValue(record.getResponseBody(), InvokeResponse.class).withReplayed(true); }
                catch (Exception ex) { throw new BusinessException(ErrorCode.INTERNAL_ERROR, "幂等结果读取失败"); }
            }
            throw new BusinessException(ErrorCode.CONFLICT, "相同请求正在处理中");
        }

        IdempotencyRecordEntity idem = new IdempotencyRecordEntity();
        OffsetDateTime now = OffsetDateTime.now();
        idem.setId(UUID.randomUUID().toString()); idem.setScope(scope); idem.setIdempotencyKey(key); idem.setRequestHash(requestHash); idem.setState("PROCESSING");
        idem.setCreatedAt(now); idem.setUpdatedAt(now); idem.setExpiresAt(now.plusHours(24));
        try { idempotencyRepository.saveAndFlush(idem); }
        catch (DataIntegrityViolationException ex) { throw new BusinessException(ErrorCode.CONFLICT, "相同请求正在处理中"); }

        long start = System.nanoTime();
        int attempts = 0;
        Map<String, Object> raw = null;
        RestClientException last = null;
        while (attempts < properties.getAgent().getMaxAttempts()) {
            attempts++;
            try {
                Map<String, Object> outbound = new LinkedHashMap<>();
                outbound.put("requestId", RequestContext.requestId());
                outbound.put("moduleCode", module);
                outbound.put("operation", operation);
                outbound.put("input", request.input() == null ? Map.of() : request.input());
                outbound.put("timeoutMs", timeout);
                raw = client.post().uri("/v1/invoke").body(outbound).retrieve().body(new org.springframework.core.ParameterizedTypeReference<Map<String, Object>>() {});
                break;
            } catch (RestClientException ex) {
                last = ex;
                if (attempts < properties.getAgent().getMaxAttempts()) sleep(properties.getAgent().getRetryBackoffMs() * attempts);
            }
        }
        long latencyMs = (System.nanoTime() - start) / 1_000_000;
        if (raw == null) {
            String code = latencyMs >= timeout ? ErrorCode.AGENT_TIMEOUT.name() : ErrorCode.AGENT_UNAVAILABLE.name();
            saveLog(actor.id(), module, operation, "MOCK_OR_REMOTE", "FAILED", attempts, timeout, latencyMs, key, requestHash, null, code, safeMessage(last));
            idem.setState("FAILED"); idem.setUpdatedAt(OffsetDateTime.now()); idempotencyRepository.save(idem);
            audit.record(actor.id(), actor.getUsername(), "AI_INVOKE", "AI_CALL", idem.getId(), "FAILED", null,
                    jsons.write(Map.of("module", module, "operation", operation)));
            throw new BusinessException(code.equals(ErrorCode.AGENT_TIMEOUT.name()) ? ErrorCode.AGENT_TIMEOUT : ErrorCode.AGENT_UNAVAILABLE, "Agent 服务暂不可用，已完成重试并记录审计");
        }

        String callId = UUID.randomUUID().toString();
        InvokeResponse response = new InvokeResponse(callId, "SUCCEEDED", raw, attempts, latencyMs, false);
        String responseJson = jsons.write(response);
        idem.setState("COMPLETED"); idem.setResponseStatus(200); idem.setResponseBody(responseJson); idem.setUpdatedAt(OffsetDateTime.now()); idempotencyRepository.save(idem);
        saveLog(actor.id(), module, operation, "MOCK_OR_REMOTE", "SUCCEEDED", attempts, timeout, latencyMs, key, requestHash, Hashes.sha256(responseJson), null, null);
        audit.record(actor.id(), actor.getUsername(), "AI_INVOKE", "AI_CALL", callId, "SUCCESS", null,
                jsons.write(Map.of("module", module, "operation", operation)));
        return response;
    }

    @Transactional(readOnly = true)
    public List<CallLogView> listLogs() {
        var actor = SecurityUtils.current();
        var rows = actor.permissions().contains("ai:log:read:all") ? logs.findTop100ByOrderByCreatedAtDesc() : logs.findTop100ByActorUserIdOrderByCreatedAtDesc(actor.id());
        return rows.stream().map(CallLogView::from).toList();
    }

    private void saveLog(String actorId, String module, String operation, String provider, String status, int attempts, int timeout, long latency, String key, String inputDigest, String outputDigest, String errorCode, String errorMessage) {
        AiCallLogEntity e = new AiCallLogEntity();
        e.setId(UUID.randomUUID().toString()); e.setActorUserId(actorId); e.setModuleCode(module); e.setOperation(operation); e.setProviderMode(provider); e.setStatus(status); e.setAttempts(attempts); e.setTimeoutMs(timeout); e.setLatencyMs(latency); e.setRequestId(RequestContext.requestId()); e.setIdempotencyKey(key); e.setInputDigest(inputDigest); e.setOutputDigest(outputDigest); e.setErrorCode(errorCode); e.setErrorMessage(errorMessage); e.setCreatedAt(OffsetDateTime.now()); logs.save(e);
    }
    private static String validateKey(String key) {
        if (key == null || key.isBlank() || key.length() > 120 || !key.matches("[A-Za-z0-9._:-]{8,120}")) throw new BusinessException(ErrorCode.INVALID_ARGUMENT, "写操作必须提供合法的 Idempotency-Key（8-120 位）");
        return key;
    }
    private static String normalizeCode(String value) { String v = value.trim().toUpperCase(); if (!v.matches("[A-Z0-9_-]{2,50}")) throw new BusinessException(ErrorCode.INVALID_ARGUMENT, "moduleCode 格式不正确"); return v; }
    private static String normalizeOperation(String value) { String v = value.trim(); if (!v.matches("[A-Za-z0-9._:-]{2,100}")) throw new BusinessException(ErrorCode.INVALID_ARGUMENT, "operation 格式不正确"); return v; }
    private static void sleep(long ms) { try { Thread.sleep(ms); } catch (InterruptedException e) { Thread.currentThread().interrupt(); } }
    private static String safeMessage(Exception ex) { if (ex == null || ex.getMessage() == null) return null; String m = ex.getMessage().replaceAll("(?i)(token|secret|password)=[^&\\s]+", "$1=***"); return m.substring(0, Math.min(500, m.length())); }

    public record InvokeRequest(String moduleCode, String operation, Map<String, Object> input, Integer timeoutMs) {}
    public record InvokeResponse(String callId, String status, Map<String, Object> data, int attempts, long latencyMs, boolean replayed) { InvokeResponse withReplayed(boolean value) { return new InvokeResponse(callId, status, data, attempts, latencyMs, value); } }
    public record CallLogView(String id, String moduleCode, String operation, String status, int attempts, int timeoutMs, long latencyMs, String requestId, String errorCode, OffsetDateTime createdAt) { static CallLogView from(AiCallLogEntity e) { return new CallLogView(e.getId(), e.getModuleCode(), e.getOperation(), e.getStatus(), e.getAttempts(), e.getTimeoutMs(), e.getLatencyMs(), e.getRequestId(), e.getErrorCode(), e.getCreatedAt()); } }
}
