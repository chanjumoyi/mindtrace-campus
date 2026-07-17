package com.xinji.foundation.audit;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

public interface AuditLogRepository extends JpaRepository<AuditLogEntity, String> {
    Page<AuditLogEntity> findAllByOrderByOccurredAtDesc(Pageable pageable);
}
