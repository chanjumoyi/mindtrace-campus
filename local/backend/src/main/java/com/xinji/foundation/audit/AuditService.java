package com.xinji.foundation.audit;

import com.xinji.foundation.common.RequestContext;
import java.time.OffsetDateTime;
import java.util.UUID;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

@Service
public class AuditService {
    private final AuditLogRepository repository;
    public AuditService(AuditLogRepository repository) { this.repository = repository; }

    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public void record(String actorUserId, String actorUsername, String action, String resourceType, String resourceId, String result, String ip, String detailJson) {
        AuditLogEntity e = new AuditLogEntity();
        e.setId(UUID.randomUUID().toString());
        e.setActorUserId(actorUserId);
        e.setActorUsername(actorUsername);
        e.setAction(action);
        e.setResourceType(resourceType);
        e.setResourceId(resourceId);
        e.setResult(result);
        e.setRequestId(RequestContext.requestId());
        e.setIpAddress(ip);
        e.setDetailJson(redact(detailJson));
        e.setOccurredAt(OffsetDateTime.now());
        repository.save(e);
    }

    @Transactional(readOnly = true)
    public Page<AuditView> list(int page, int size) {
        int safePage = Math.max(page, 0);
        int safeSize = Math.max(1, Math.min(size, 100));
        return repository.findAllByOrderByOccurredAtDesc(PageRequest.of(safePage, safeSize)).map(AuditView::from);
    }

    private static String redact(String detail) {
        if (detail == null) return null;
        String value = detail.replaceAll("(?i)(password|token|secret)(\"?\\s*[:=]\\s*\"?)[^\",}\\s]+", "$1$2***");
        return value.length() > 4000 ? value.substring(0, 4000) : value;
    }

    public record AuditView(String id, String actorUsername, String action, String resourceType, String resourceId, String result, String requestId, OffsetDateTime occurredAt) {
        static AuditView from(AuditLogEntity e) {
            return new AuditView(e.getId(), e.getActorUsername(), e.getAction(), e.getResourceType(), e.getResourceId(), e.getResult(), e.getRequestId(), e.getOccurredAt());
        }
    }
}
