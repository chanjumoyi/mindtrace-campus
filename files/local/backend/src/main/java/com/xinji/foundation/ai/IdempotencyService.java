package com.xinji.foundation.ai;

import com.xinji.foundation.common.BusinessException;
import com.xinji.foundation.common.ErrorCode;
import com.xinji.foundation.common.IdempotencyInProgressException;
import com.xinji.foundation.config.XinjiProperties;
import java.time.Duration;
import java.time.OffsetDateTime;
import java.util.UUID;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

@Service
public class IdempotencyService {
    private final IdempotencyRecordRepository repository;
    private final XinjiProperties properties;

    public IdempotencyService(IdempotencyRecordRepository repository, XinjiProperties properties) {
        this.repository = repository;
        this.properties = properties;
    }

    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public AcquireResult acquire(String scope, String key, String requestHash, int requestTimeoutMs) {
        OffsetDateTime now = OffsetDateTime.now();
        OffsetDateTime leaseUntil = now.plus(Duration.ofMillis((long) requestTimeoutMs + properties.getAgent().getIdempotencyLeaseGraceMs()));
        OffsetDateTime expiresAt = now.plusHours(properties.getAgent().getIdempotencyTtlHours());

        var existing = repository.findLocked(scope, key);
        if (existing.isEmpty()) {
            IdempotencyRecordEntity created = new IdempotencyRecordEntity();
            created.setId(UUID.randomUUID().toString());
            created.setScope(scope);
            created.setIdempotencyKey(key);
            created.setRequestHash(requestHash);
            created.setState("PROCESSING");
            created.setLeaseUntil(leaseUntil);
            created.setExpiresAt(expiresAt);
            created.setRecoveryCount(0);
            created.setCreatedAt(now);
            created.setUpdatedAt(now);
            try {
                repository.saveAndFlush(created);
                return AcquireResult.acquired(created.getId(), 0);
            } catch (DataIntegrityViolationException ex) {
                throw new IdempotencyInProgressException(1);
            }
        }

        IdempotencyRecordEntity record = existing.get();
        boolean expired = record.getExpiresAt() == null || !record.getExpiresAt().isAfter(now);
        if (!expired && !record.getRequestHash().equals(requestHash)) {
            throw new BusinessException(ErrorCode.IDEMPOTENCY_CONFLICT, "相同 Idempotency-Key 对应了不同请求");
        }
        if (!expired && "COMPLETED".equals(record.getState()) && record.getResponseBody() != null) {
            return AcquireResult.replayed(record.getId(), record.getResponseBody(), record.getSourceCallId(), record.getRecoveryCount());
        }
        if (!expired && "PROCESSING".equals(record.getState()) && record.getLeaseUntil() != null && record.getLeaseUntil().isAfter(now)) {
            long seconds = Math.max(1, Duration.between(now, record.getLeaseUntil()).toSeconds());
            throw new IdempotencyInProgressException(seconds);
        }

        int recoveryCount = record.getRecoveryCount();
        if ("FAILED".equals(record.getState()) || "PROCESSING".equals(record.getState())) recoveryCount++;
        record.setRequestHash(requestHash);
        record.setState("PROCESSING");
        record.setResponseStatus(null);
        record.setResponseBody(null);
        record.setSourceCallId(null);
        record.setLastErrorCode(null);
        record.setLeaseUntil(leaseUntil);
        record.setExpiresAt(expiresAt);
        record.setRecoveryCount(recoveryCount);
        record.setUpdatedAt(now);
        repository.save(record);
        return AcquireResult.acquired(record.getId(), recoveryCount);
    }

    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public void completeSuccess(String id, String sourceCallId, int responseStatus, String responseBody) {
        IdempotencyRecordEntity record = repository.findLockedById(id)
                .orElseThrow(() -> new BusinessException(ErrorCode.INTERNAL_ERROR, "幂等记录不存在"));
        record.setState("COMPLETED");
        record.setSourceCallId(sourceCallId);
        record.setResponseStatus(responseStatus);
        record.setResponseBody(responseBody);
        record.setLastErrorCode(null);
        record.setLeaseUntil(null);
        record.setUpdatedAt(OffsetDateTime.now());
        repository.save(record);
    }

    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public void completeFailure(String id, String errorCode) {
        repository.findLockedById(id).ifPresent(record -> {
            record.setState("FAILED");
            record.setLastErrorCode(errorCode);
            record.setResponseStatus(null);
            record.setResponseBody(null);
            record.setLeaseUntil(null);
            record.setUpdatedAt(OffsetDateTime.now());
            repository.save(record);
        });
    }

    @Scheduled(fixedDelayString = "${xinji.agent.cleanup-interval-ms:300000}")
    @Transactional
    public void cleanupExpired() {
        repository.deleteExpired(OffsetDateTime.now());
    }

    public record AcquireResult(boolean replayed, String recordId, String responseBody, String sourceCallId, int recoveryCount) {
        static AcquireResult acquired(String recordId, int recoveryCount) {
            return new AcquireResult(false, recordId, null, null, recoveryCount);
        }
        static AcquireResult replayed(String recordId, String responseBody, String sourceCallId, int recoveryCount) {
            return new AcquireResult(true, recordId, responseBody, sourceCallId, recoveryCount);
        }
    }
}
