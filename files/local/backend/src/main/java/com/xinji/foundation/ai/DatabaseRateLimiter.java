package com.xinji.foundation.ai;

import com.xinji.foundation.common.RateLimitExceededException;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.UUID;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.TransactionDefinition;
import org.springframework.transaction.support.TransactionTemplate;

@Service
public class DatabaseRateLimiter {
    private final AiRateLimitBucketRepository repository;
    private final TransactionTemplate transaction;

    public DatabaseRateLimiter(AiRateLimitBucketRepository repository, PlatformTransactionManager transactionManager) {
        this.repository = repository;
        this.transaction = new TransactionTemplate(transactionManager);
        this.transaction.setPropagationBehavior(TransactionDefinition.PROPAGATION_REQUIRES_NEW);
    }

    public RateLimitDecision check(String scope, int limit, int windowSeconds) {
        if (limit <= 0 || windowSeconds <= 0) return new RateLimitDecision(Integer.MAX_VALUE, 0, Integer.MAX_VALUE);
        for (int attempt = 0; attempt < 3; attempt++) {
            try {
                RateLimitDecision decision = transaction.execute(status -> increment(scope, limit, windowSeconds));
                if (decision == null) throw new IllegalStateException("Rate limit transaction returned no result");
                return decision;
            } catch (DataIntegrityViolationException ex) {
                if (attempt == 2) throw ex;
            }
        }
        throw new IllegalStateException("Unable to update rate limit bucket");
    }

    private RateLimitDecision increment(String scope, int limit, int windowSeconds) {
        long nowEpoch = Instant.now().getEpochSecond();
        long windowEpoch = (nowEpoch / windowSeconds) * windowSeconds;
        OffsetDateTime windowStart = OffsetDateTime.ofInstant(Instant.ofEpochSecond(windowEpoch), ZoneOffset.UTC);
        OffsetDateTime windowEnd = windowStart.plusSeconds(windowSeconds);
        long retryAfter = Math.max(1, windowEnd.toEpochSecond() - nowEpoch);

        AiRateLimitBucketEntity bucket = repository.findLocked(scope, windowStart).orElse(null);
        if (bucket == null) {
            bucket = new AiRateLimitBucketEntity();
            bucket.setId(UUID.nameUUIDFromBytes((scope + ":" + windowEpoch).getBytes(StandardCharsets.UTF_8)).toString());
            bucket.setScope(scope);
            bucket.setWindowStart(windowStart);
            bucket.setRequestCount(0);
            bucket.setExpiresAt(windowEnd.plusSeconds(windowSeconds));
        }
        if (bucket.getRequestCount() >= limit) throw new RateLimitExceededException(retryAfter, limit);
        bucket.setRequestCount(bucket.getRequestCount() + 1);
        repository.saveAndFlush(bucket);
        return new RateLimitDecision(limit - bucket.getRequestCount(), retryAfter, limit);
    }

    @Scheduled(fixedDelayString = "${xinji.agent.cleanup-interval-ms:300000}")
    public void cleanupExpired() {
        transaction.executeWithoutResult(status -> repository.deleteExpired(OffsetDateTime.now(ZoneOffset.UTC)));
    }

    public record RateLimitDecision(int remaining, long retryAfterSeconds, int limit) {}
}
