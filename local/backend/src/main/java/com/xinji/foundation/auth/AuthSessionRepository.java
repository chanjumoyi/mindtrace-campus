package com.xinji.foundation.auth;

import java.time.OffsetDateTime;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface AuthSessionRepository extends JpaRepository<AuthSessionEntity, String> {
    Optional<AuthSessionEntity> findByTokenHashAndRevokedAtIsNullAndExpiresAtAfter(String tokenHash, OffsetDateTime now);
    @Modifying
    @Query("update AuthSessionEntity s set s.revokedAt = :now where s.userId = :userId and s.revokedAt is null")
    int revokeAllForUser(@Param("userId") String userId, @Param("now") OffsetDateTime now);
}
