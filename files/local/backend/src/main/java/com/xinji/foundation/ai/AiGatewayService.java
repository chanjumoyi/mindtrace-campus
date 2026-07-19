package com.xinji.foundation.ai;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.xinji.foundation.audit.AuditService;
import com.xinji.foundation.auth.SecurityUtils;
import com.xinji.foundation.common.BusinessException;
import com.xinji.foundation.common.ErrorCode;
import com.xinji.foundation.common.Hashes;
import com.xinji.foundation.common.Jsons;
import com.xinji.foundation.common.RateLimitExceededException;
import com.xinji.foundation.common.RequestContext;
import com.xinji.foundation.config.XinjiProperties;
import java.io.IOException;
import java.net.ConnectException;
import java.net.http.HttpTimeoutException;
import java.time.OffsetDateTime;
import java.util.LinkedHashMap;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.concurrent.ThreadLocalRandom;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class AiGatewayService {
    private final AgentHttpClient client;
    private final XinjiProperties properties;
    private final IdempotencyService idempotency;
    private final AiCallLogRepository logs;
    private final AiCallLogService logService;
    private final ObjectMapper mapper;
    private final Jsons jsons;
    private final AuditService audit;
    private final DatabaseRateLimiter rateLimiter;

    public AiGatewayService(AgentHttpClient client, XinjiProperties properties, IdempotencyService idempotency,
                            AiCallLogRepository logs, AiCallLogService logService, ObjectMapper mapper, Jsons jsons,
                            AuditService audit, DatabaseRateLimiter rateLimiter) {
        this.client = client;
        this.properties = properties;
        this.idempotency = idempotency;
        this.logs = logs;
        this.logService = logService;
        this.mapper = mapper;
        this.jsons = jsons;
        this.audit = audit;
        this.rateLimiter = rateLimiter;
    }

    public InvokeResponse invoke(String idempotencyKey, InvokeRequest request) {
        var actor = SecurityUtils.current();
        String key = validateKey(idempotencyKey);
        String module = normalizeCode(request.moduleCode());
        String operation = normalizeOperation(request.operation());
        int timeout = normalizeTimeout(request.timeoutMs());
        String requestId = RequestContext.requestId();
        String scope = "AI_INVOKE:" + actor.id();
        String requestJson = jsons.write(canonicalize(Map.of(
                "moduleCode", module,
                "operation", operation,
                "input", request.input() == null ? Map.of() : request.input(),
                "timeoutMs", timeout)));
        String requestHash = Hashes.sha256(requestJson);

        IdempotencyService.AcquireResult acquired;
        try {
            acquired = idempotency.acquire(scope, key, requestHash, timeout);
        } catch (BusinessException ex) {
            String callId = logService.recordRejected(actor.id(), module, operation, timeout, requestId, key, requestHash,
                    "IDEMPOTENCY_REJECTED", ex.getErrorCode().name(), ex.getMessage());
            audit.record(actor.id(), actor.getUsername(), "AI_INVOKE", "AI_CALL", callId, "REJECTED", null,
                    jsons.write(Map.of("module", module, "operation", operation, "errorCode", ex.getErrorCode().name())));
            throw ex;
        }
        if (acquired.replayed()) {
            try {
                InvokeResponse response = mapper.readValue(acquired.responseBody(), InvokeResponse.class).withReplayed(true);
                logService.recordReplay(actor.id(), module, operation, timeout, requestId, key, requestHash,
                        Hashes.sha256(acquired.responseBody()), acquired.sourceCallId());
                audit.record(actor.id(), actor.getUsername(), "AI_INVOKE_REPLAY", "AI_CALL", response.callId(), "SUCCESS", null,
                        jsons.write(Map.of("module", module, "operation", operation, "recoveryCount", acquired.recoveryCount())));
                return response;
            } catch (Exception ex) {
                throw new BusinessException(ErrorCode.INTERNAL_ERROR, "幂等结果读取失败");
            }
        }

        try {
            rateLimiter.check("AI_INVOKE:" + actor.id(), properties.getAgent().getRateLimitMaxRequests(),
                    properties.getAgent().getRateLimitWindowSeconds());
        } catch (RateLimitExceededException ex) {
            idempotency.completeFailure(acquired.recordId(), ErrorCode.RATE_LIMITED.name());
            String callId = logService.recordRateLimited(actor.id(), module, operation, timeout, requestId, key, requestHash, ex.getMessage());
            audit.record(actor.id(), actor.getUsername(), "AI_INVOKE", "AI_CALL", callId, "FAILED", null,
                    jsons.write(Map.of("module", module, "operation", operation, "errorCode", ErrorCode.RATE_LIMITED.name())));
            throw ex;
        }

        String callId;
        try {
            callId = logService.start(actor.id(), module, operation, timeout, requestId, key, requestHash);
        } catch (RuntimeException ex) {
            idempotency.completeFailure(acquired.recordId(), ErrorCode.INTERNAL_ERROR.name());
            throw ex;
        }
        long startedNanos = System.nanoTime();
        long deadlineNanos = startedNanos + timeout * 1_000_000L;
        int attempts = 0;
        long totalBackoffMs = 0;
        Integer lastHttpStatus = null;
        ErrorCode finalError = ErrorCode.AGENT_UNAVAILABLE;
        String finalMessage = "Agent 服务暂不可用";
        Map<String, Object> raw = null;

        Map<String, Object> outbound = new LinkedHashMap<>();
        outbound.put("requestId", requestId);
        outbound.put("moduleCode", module);
        outbound.put("operation", operation);
        outbound.put("input", request.input() == null ? Map.of() : request.input());
        outbound.put("timeoutMs", timeout);

        while (attempts < properties.getAgent().getMaxAttempts()) {
            long remainingMs = remainingMs(deadlineNanos);
            if (remainingMs <= 0) {
                finalError = ErrorCode.AGENT_TIMEOUT;
                finalMessage = "Agent 调用超过请求总超时时间";
                break;
            }

            attempts++;
            int attemptTimeoutMs = (int) Math.max(1, Math.min(remainingMs, properties.getAgent().getPerAttemptTimeoutMs()));
            OffsetDateTime attemptStartedAt = OffsetDateTime.now();
            long attemptStartedNanos = System.nanoTime();
            String attemptStatus;
            boolean retryable;
            Integer attemptHttpStatus = null;
            String attemptErrorCode = null;
            String attemptErrorMessage = null;
            long backoffMs = 0;

            try {
                AgentHttpClient.TransportResponse response = client.invoke(outbound, attemptTimeoutMs, requestId, key);
                attemptHttpStatus = response.statusCode();
                lastHttpStatus = attemptHttpStatus;
                if (response.statusCode() >= 200 && response.statusCode() < 300) {
                    raw = response.body();
                    attemptStatus = "SUCCEEDED";
                    retryable = false;
                } else {
                    retryable = isRetryableStatus(response.statusCode());
                    finalError = retryable ? ErrorCode.AGENT_UNAVAILABLE : ErrorCode.AGENT_REJECTED;
                    finalMessage = "Agent 返回 HTTP " + response.statusCode();
                    attemptStatus = "HTTP_ERROR";
                    attemptErrorCode = finalError.name();
                    attemptErrorMessage = response.safeBody();
                    if (shouldRetry(attempts, retryable, deadlineNanos)) {
                        backoffMs = calculateBackoffMs(attempts, response.retryAfterMs(), deadlineNanos);
                    }
                }
            } catch (HttpTimeoutException ex) {
                retryable = true;
                finalError = ErrorCode.AGENT_TIMEOUT;
                finalMessage = "Agent 单次调用超时";
                attemptStatus = "TIMEOUT";
                attemptErrorCode = finalError.name();
                attemptErrorMessage = safeMessage(ex);
                if (shouldRetry(attempts, true, deadlineNanos)) backoffMs = calculateBackoffMs(attempts, null, deadlineNanos);
            } catch (AgentHttpClient.AgentProtocolException ex) {
                retryable = true;
                finalError = ErrorCode.AGENT_BAD_RESPONSE;
                finalMessage = "Agent 返回的数据格式不正确";
                attemptStatus = "BAD_RESPONSE";
                attemptErrorCode = finalError.name();
                attemptErrorMessage = safeMessage(ex);
                if (shouldRetry(attempts, true, deadlineNanos)) backoffMs = calculateBackoffMs(attempts, null, deadlineNanos);
            } catch (ConnectException ex) {
                retryable = true;
                finalError = ErrorCode.AGENT_UNAVAILABLE;
                finalMessage = "无法连接 Agent 服务";
                attemptStatus = "CONNECT_ERROR";
                attemptErrorCode = finalError.name();
                attemptErrorMessage = safeMessage(ex);
                if (shouldRetry(attempts, true, deadlineNanos)) backoffMs = calculateBackoffMs(attempts, null, deadlineNanos);
            } catch (IOException ex) {
                retryable = true;
                finalError = ErrorCode.AGENT_UNAVAILABLE;
                finalMessage = "Agent 网络调用失败";
                attemptStatus = "IO_ERROR";
                attemptErrorCode = finalError.name();
                attemptErrorMessage = safeMessage(ex);
                if (shouldRetry(attempts, true, deadlineNanos)) backoffMs = calculateBackoffMs(attempts, null, deadlineNanos);
            } catch (InterruptedException ex) {
                Thread.currentThread().interrupt();
                retryable = false;
                finalError = ErrorCode.AGENT_UNAVAILABLE;
                finalMessage = "Agent 调用被中断";
                attemptStatus = "INTERRUPTED";
                attemptErrorCode = finalError.name();
                attemptErrorMessage = safeMessage(ex);
            } catch (RuntimeException ex) {
                retryable = false;
                finalError = ErrorCode.INTERNAL_ERROR;
                finalMessage = "Agent 网关内部处理失败";
                attemptStatus = "INTERNAL_ERROR";
                attemptErrorCode = finalError.name();
                attemptErrorMessage = safeMessage(ex);
            }

            long attemptLatencyMs = elapsedMs(attemptStartedNanos);
            logService.recordAttempt(callId, attempts, raw != null ? "SUCCEEDED" : attemptStatus, attemptLatencyMs,
                    attemptHttpStatus, raw == null && retryable, backoffMs, attemptErrorCode, attemptErrorMessage,
                    attemptStartedAt, OffsetDateTime.now());

            if (raw != null) break;
            if (backoffMs <= 0) break;
            if (!sleep(backoffMs)) {
                finalError = ErrorCode.AGENT_UNAVAILABLE;
                finalMessage = "Agent 重试等待被中断";
                break;
            }
            totalBackoffMs += backoffMs;
        }

        long latencyMs = elapsedMs(startedNanos);
        if (raw == null) {
            if (remainingMs(deadlineNanos) <= 0) {
                finalError = ErrorCode.AGENT_TIMEOUT;
                finalMessage = "Agent 调用超过请求总超时时间";
            }
            idempotency.completeFailure(acquired.recordId(), finalError.name());
            logService.completeFailure(callId, attempts, latencyMs, totalBackoffMs, lastHttpStatus, finalError.name(), finalMessage);
            audit.record(actor.id(), actor.getUsername(), "AI_INVOKE", "AI_CALL", callId, "FAILED", null,
                    jsons.write(Map.of("module", module, "operation", operation, "attempts", attempts,
                            "errorCode", finalError.name(), "recoveryCount", acquired.recoveryCount())));
            throw new BusinessException(finalError, finalMessage + "，已完成重试、日志与审计记录");
        }

        InvokeResponse response = new InvokeResponse(callId, "SUCCEEDED", raw, attempts, latencyMs, false);
        String responseJson = jsons.write(response);
        idempotency.completeSuccess(acquired.recordId(), callId, 200, responseJson);
        logService.completeSuccess(callId, attempts, latencyMs, totalBackoffMs, lastHttpStatus, Hashes.sha256(responseJson));
        audit.record(actor.id(), actor.getUsername(), "AI_INVOKE", "AI_CALL", callId, "SUCCESS", null,
                jsons.write(Map.of("module", module, "operation", operation, "attempts", attempts,
                        "recoveryCount", acquired.recoveryCount())));
        return response;
    }

    @Transactional(readOnly = true)
    public List<CallLogView> listLogs() {
        var actor = SecurityUtils.current();
        var rows = actor.permissions().contains("ai:log:read:all")
                ? logs.findTop100ByOrderByCreatedAtDesc()
                : logs.findTop100ByActorUserIdOrderByCreatedAtDesc(actor.id());
        return rows.stream().map(CallLogView::from).toList();
    }

    @Transactional(readOnly = true)
    public List<AttemptLogView> listAttempts(String callId) {
        var actor = SecurityUtils.current();
        AiCallLogEntity call = logs.findById(callId).orElseThrow(() -> new BusinessException(ErrorCode.NOT_FOUND, "AI 调用日志不存在"));
        if (!actor.permissions().contains("ai:log:read:all") && !actor.id().equals(call.getActorUserId())) {
            throw new BusinessException(ErrorCode.FORBIDDEN, "无权查看该调用的重试日志");
        }
        return logService.attempts(callId).stream().map(AttemptLogView::from).toList();
    }


    private static Object canonicalize(Object value) {
        if (value instanceof Map<?, ?> map) {
            Map<String, Object> sorted = new TreeMap<>();
            map.forEach((key, item) -> sorted.put(String.valueOf(key), canonicalize(item)));
            return sorted;
        }
        if (value instanceof List<?> list) {
            List<Object> canonical = new ArrayList<>(list.size());
            list.forEach(item -> canonical.add(canonicalize(item)));
            return canonical;
        }
        return value;
    }

    private int normalizeTimeout(Integer requested) {
        int max = properties.getAgent().getTimeoutMs();
        int min = Math.min(properties.getAgent().getMinTimeoutMs(), max);
        if (requested == null) return max;
        return Math.max(min, Math.min(requested, max));
    }

    private boolean shouldRetry(int attempts, boolean retryable, long deadlineNanos) {
        return retryable && attempts < properties.getAgent().getMaxAttempts() && remainingMs(deadlineNanos) > 1;
    }

    private long calculateBackoffMs(int attempt, Long retryAfterMs, long deadlineNanos) {
        long exponential;
        if (attempt >= 31) exponential = properties.getAgent().getRetryMaxBackoffMs();
        else exponential = properties.getAgent().getRetryBackoffMs() * (1L << Math.max(0, attempt - 1));
        long jitter = properties.getAgent().getRetryJitterMs() <= 0 ? 0
                : ThreadLocalRandom.current().nextLong(properties.getAgent().getRetryJitterMs() + 1);
        long candidate = Math.min(properties.getAgent().getRetryMaxBackoffMs(), exponential + jitter);
        if (retryAfterMs != null) candidate = Math.max(candidate, retryAfterMs);
        long remaining = remainingMs(deadlineNanos);
        return Math.max(0, Math.min(candidate, Math.max(0, remaining - 1)));
    }

    private static boolean isRetryableStatus(int status) {
        return status == 408 || status == 425 || status == 429 || status == 500 || status == 502 || status == 503 || status == 504;
    }

    private static long remainingMs(long deadlineNanos) {
        long nanos = deadlineNanos - System.nanoTime();
        return nanos <= 0 ? 0 : Math.max(1, nanos / 1_000_000L);
    }

    private static long elapsedMs(long startedNanos) {
        return Math.max(0, (System.nanoTime() - startedNanos) / 1_000_000L);
    }

    private static boolean sleep(long ms) {
        try {
            Thread.sleep(ms);
            return true;
        } catch (InterruptedException ex) {
            Thread.currentThread().interrupt();
            return false;
        }
    }

    private static String validateKey(String key) {
        if (key == null || key.isBlank() || key.length() > 120 || !key.matches("[A-Za-z0-9._:-]{8,120}")) {
            throw new BusinessException(ErrorCode.INVALID_ARGUMENT, "写操作必须提供合法的 Idempotency-Key（8-120 位）");
        }
        return key;
    }

    private static String normalizeCode(String value) {
        if (value == null) throw new BusinessException(ErrorCode.INVALID_ARGUMENT, "moduleCode 不能为空");
        String normalized = value.trim().toUpperCase();
        if (!normalized.matches("[A-Z0-9_-]{2,50}")) throw new BusinessException(ErrorCode.INVALID_ARGUMENT, "moduleCode 格式不正确");
        return normalized;
    }

    private static String normalizeOperation(String value) {
        if (value == null) throw new BusinessException(ErrorCode.INVALID_ARGUMENT, "operation 不能为空");
        String normalized = value.trim();
        if (!normalized.matches("[A-Za-z0-9._:-]{2,100}")) throw new BusinessException(ErrorCode.INVALID_ARGUMENT, "operation 格式不正确");
        return normalized;
    }

    private static String safeMessage(Exception ex) {
        if (ex == null || ex.getMessage() == null) return null;
        String message = ex.getMessage().replaceAll("(?i)(token|secret|password|authorization)(\\s*[:=]\\s*)[^&\\s]+", "$1$2***");
        return message.substring(0, Math.min(500, message.length()));
    }

    public record InvokeRequest(String moduleCode, String operation, Map<String, Object> input, Integer timeoutMs) {}

    public record InvokeResponse(String callId, String status, Map<String, Object> data, int attempts, long latencyMs, boolean replayed) {
        InvokeResponse withReplayed(boolean value) { return new InvokeResponse(callId, status, data, attempts, latencyMs, value); }
    }

    public record CallLogView(String id, String moduleCode, String operation, String status, int attempts, int timeoutMs,
                              long latencyMs, long totalBackoffMs, Integer httpStatus, boolean replayed, String parentCallId,
                              String requestId, String errorCode, OffsetDateTime startedAt, OffsetDateTime completedAt) {
        static CallLogView from(AiCallLogEntity entity) {
            return new CallLogView(entity.getId(), entity.getModuleCode(), entity.getOperation(), entity.getStatus(),
                    entity.getAttempts(), entity.getTimeoutMs(), entity.getLatencyMs(), entity.getTotalBackoffMs(),
                    entity.getHttpStatus(), entity.isReplayed(), entity.getParentCallId(), entity.getRequestId(),
                    entity.getErrorCode(), entity.getStartedAt(), entity.getCompletedAt());
        }
    }

    public record AttemptLogView(int attemptNo, String status, long latencyMs, Integer httpStatus, boolean retryable,
                                 long backoffMs, String errorCode, String errorMessage, OffsetDateTime startedAt,
                                 OffsetDateTime completedAt) {
        static AttemptLogView from(AiCallAttemptLogEntity entity) {
            return new AttemptLogView(entity.getAttemptNo(), entity.getStatus(), entity.getLatencyMs(), entity.getHttpStatus(),
                    entity.isRetryable(), entity.getBackoffMs(), entity.getErrorCode(), entity.getErrorMessage(),
                    entity.getStartedAt(), entity.getCompletedAt());
        }
    }
}
