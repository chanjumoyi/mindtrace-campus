package com.xinji.foundation.ai;

import io.micrometer.core.instrument.MeterRegistry;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

@Service
public class AiCallLogService {
    private final AiCallLogRepository calls;
    private final AiCallAttemptLogRepository attempts;
    private final MeterRegistry metrics;

    public AiCallLogService(AiCallLogRepository calls, AiCallAttemptLogRepository attempts, MeterRegistry metrics) {
        this.calls = calls;
        this.attempts = attempts;
        this.metrics = metrics;
    }

    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public String start(String actorId, String module, String operation, int timeoutMs, String requestId, String idempotencyKey, String inputDigest) {
        OffsetDateTime now = OffsetDateTime.now();
        AiCallLogEntity entity = base(actorId, module, operation, timeoutMs, requestId, idempotencyKey, inputDigest, now);
        entity.setStatus("PROCESSING");
        calls.save(entity);
        return entity.getId();
    }

    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public String recordReplay(String actorId, String module, String operation, int timeoutMs, String requestId, String idempotencyKey,
                               String inputDigest, String outputDigest, String parentCallId) {
        OffsetDateTime now = OffsetDateTime.now();
        AiCallLogEntity entity = base(actorId, module, operation, timeoutMs, requestId, idempotencyKey, inputDigest, now);
        entity.setStatus("REPLAYED");
        entity.setReplayed(true);
        entity.setParentCallId(parentCallId);
        entity.setOutputDigest(outputDigest);
        entity.setCompletedAt(now);
        calls.save(entity);
        metrics.counter("xinji.ai.calls", "module", module, "status", "REPLAYED").increment();
        return entity.getId();
    }


    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public String recordRejected(String actorId, String module, String operation, int timeoutMs, String requestId,
                                 String idempotencyKey, String inputDigest, String status, String errorCode, String message) {
        OffsetDateTime now = OffsetDateTime.now();
        AiCallLogEntity entity = base(actorId, module, operation, timeoutMs, requestId, idempotencyKey, inputDigest, now);
        entity.setStatus(status);
        entity.setErrorCode(errorCode);
        entity.setErrorMessage(message);
        entity.setCompletedAt(now);
        calls.save(entity);
        metrics.counter("xinji.ai.calls", "module", module, "status", status).increment();
        return entity.getId();
    }

    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public String recordRateLimited(String actorId, String module, String operation, int timeoutMs, String requestId,
                                    String idempotencyKey, String inputDigest, String message) {
        OffsetDateTime now = OffsetDateTime.now();
        AiCallLogEntity entity = base(actorId, module, operation, timeoutMs, requestId, idempotencyKey, inputDigest, now);
        entity.setStatus("RATE_LIMITED");
        entity.setErrorCode("RATE_LIMITED");
        entity.setErrorMessage(message);
        entity.setCompletedAt(now);
        calls.save(entity);
        metrics.counter("xinji.ai.calls", "module", module, "status", "RATE_LIMITED").increment();
        return entity.getId();
    }

    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public void recordAttempt(String callId, int attemptNo, String status, long latencyMs, Integer httpStatus,
                              boolean retryable, long backoffMs, String errorCode, String errorMessage,
                              OffsetDateTime startedAt, OffsetDateTime completedAt) {
        AiCallAttemptLogEntity entity = new AiCallAttemptLogEntity();
        entity.setId(UUID.randomUUID().toString());
        entity.setCallId(callId);
        entity.setAttemptNo(attemptNo);
        entity.setStatus(status);
        entity.setLatencyMs(latencyMs);
        entity.setHttpStatus(httpStatus);
        entity.setRetryable(retryable);
        entity.setBackoffMs(backoffMs);
        entity.setErrorCode(errorCode);
        entity.setErrorMessage(errorMessage);
        entity.setStartedAt(startedAt);
        entity.setCompletedAt(completedAt);
        attempts.save(entity);
        metrics.counter("xinji.ai.attempts", "status", status, "retryable", Boolean.toString(retryable)).increment();
        if (backoffMs > 0) metrics.counter("xinji.ai.retries").increment();
    }

    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public void completeSuccess(String callId, int attemptCount, long latencyMs, long totalBackoffMs, Integer httpStatus, String outputDigest) {
        AiCallLogEntity entity = calls.findById(callId).orElseThrow();
        entity.setStatus("SUCCEEDED");
        entity.setAttempts(attemptCount);
        entity.setLatencyMs(latencyMs);
        entity.setTotalBackoffMs(totalBackoffMs);
        entity.setHttpStatus(httpStatus);
        entity.setOutputDigest(outputDigest);
        entity.setCompletedAt(OffsetDateTime.now());
        calls.save(entity);
        recordMetrics(entity);
    }

    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public void completeFailure(String callId, int attemptCount, long latencyMs, long totalBackoffMs, Integer httpStatus,
                                String errorCode, String errorMessage) {
        AiCallLogEntity entity = calls.findById(callId).orElseThrow();
        entity.setStatus("FAILED");
        entity.setAttempts(attemptCount);
        entity.setLatencyMs(latencyMs);
        entity.setTotalBackoffMs(totalBackoffMs);
        entity.setHttpStatus(httpStatus);
        entity.setErrorCode(errorCode);
        entity.setErrorMessage(errorMessage);
        entity.setCompletedAt(OffsetDateTime.now());
        calls.save(entity);
        recordMetrics(entity);
    }

    @Transactional(readOnly = true)
    public List<AiCallAttemptLogEntity> attempts(String callId) {
        return attempts.findByCallIdOrderByAttemptNo(callId);
    }

    private AiCallLogEntity base(String actorId, String module, String operation, int timeoutMs, String requestId,
                                 String idempotencyKey, String inputDigest, OffsetDateTime now) {
        AiCallLogEntity entity = new AiCallLogEntity();
        entity.setId(UUID.randomUUID().toString());
        entity.setActorUserId(actorId);
        entity.setModuleCode(module);
        entity.setOperation(operation);
        entity.setProviderMode("MOCK_OR_REMOTE");
        entity.setAttempts(0);
        entity.setTimeoutMs(timeoutMs);
        entity.setLatencyMs(0);
        entity.setTotalBackoffMs(0);
        entity.setReplayed(false);
        entity.setRequestId(requestId);
        entity.setIdempotencyKey(idempotencyKey);
        entity.setInputDigest(inputDigest);
        entity.setStartedAt(now);
        entity.setCreatedAt(now);
        return entity;
    }

    private void recordMetrics(AiCallLogEntity entity) {
        metrics.counter("xinji.ai.calls", "module", entity.getModuleCode(), "status", entity.getStatus()).increment();
        metrics.timer("xinji.ai.latency", "module", entity.getModuleCode(), "status", entity.getStatus())
                .record(java.time.Duration.ofMillis(Math.max(0, entity.getLatencyMs())));
    }
}
