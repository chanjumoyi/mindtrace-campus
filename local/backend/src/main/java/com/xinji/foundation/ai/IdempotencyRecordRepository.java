package com.xinji.foundation.ai;

import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface IdempotencyRecordRepository extends JpaRepository<IdempotencyRecordEntity, String> {
    Optional<IdempotencyRecordEntity> findByScopeAndIdempotencyKey(String scope, String idempotencyKey);
}
