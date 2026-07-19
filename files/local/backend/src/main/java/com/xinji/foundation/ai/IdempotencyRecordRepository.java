package com.xinji.foundation.ai;

import jakarta.persistence.LockModeType;
import java.time.OffsetDateTime;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface IdempotencyRecordRepository extends JpaRepository<IdempotencyRecordEntity, String> {
    Optional<IdempotencyRecordEntity> findByScopeAndIdempotencyKey(String scope, String idempotencyKey);

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("select r from IdempotencyRecordEntity r where r.scope = :scope and r.idempotencyKey = :key")
    Optional<IdempotencyRecordEntity> findLocked(@Param("scope") String scope, @Param("key") String key);

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("select r from IdempotencyRecordEntity r where r.id = :id")
    Optional<IdempotencyRecordEntity> findLockedById(@Param("id") String id);

    @Modifying
    @Query("delete from IdempotencyRecordEntity r where r.expiresAt < :now and (r.state <> 'PROCESSING' or r.leaseUntil is null or r.leaseUntil < :now)")
    int deleteExpired(@Param("now") OffsetDateTime now);
}
