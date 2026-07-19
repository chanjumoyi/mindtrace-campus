package com.xinji.foundation.ai;

import jakarta.persistence.LockModeType;
import java.time.OffsetDateTime;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface AiRateLimitBucketRepository extends JpaRepository<AiRateLimitBucketEntity, String> {
    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("select b from AiRateLimitBucketEntity b where b.scope = :scope and b.windowStart = :windowStart")
    Optional<AiRateLimitBucketEntity> findLocked(@Param("scope") String scope, @Param("windowStart") OffsetDateTime windowStart);

    @Modifying
    @Query("delete from AiRateLimitBucketEntity b where b.expiresAt < :now")
    int deleteExpired(@Param("now") OffsetDateTime now);
}
