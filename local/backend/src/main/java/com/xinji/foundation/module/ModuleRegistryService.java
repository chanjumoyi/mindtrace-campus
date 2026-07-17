package com.xinji.foundation.module;

import com.xinji.foundation.audit.AuditService;
import com.xinji.foundation.auth.SecurityUtils;
import com.xinji.foundation.common.BusinessException;
import com.xinji.foundation.common.ErrorCode;
import com.xinji.foundation.common.Jsons;
import java.net.URI;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class ModuleRegistryService {
    private final ModuleRegistrationRepository repository;
    private final AuditService audit;
    private final Jsons jsons;
    public ModuleRegistryService(ModuleRegistrationRepository repository, AuditService audit, Jsons jsons) {
        this.repository = repository; this.audit = audit; this.jsons = jsons;
    }

    @Transactional(readOnly = true)
    public List<ModuleView> list() { return repository.findAll().stream().map(ModuleView::from).toList(); }

    @Transactional
    public ModuleView upsert(UpsertRequest body) {
        var actor = SecurityUtils.current();
        String code = normalizeCode(body.moduleCode());
        String owner = body.ownerCode().trim().toUpperCase();
        if (!List.of("A", "B", "C").contains(owner)) throw new BusinessException(ErrorCode.INVALID_ARGUMENT, "ownerCode 只能为 A/B/C");
        validateUrl(body.baseUrl());
        ModuleRegistrationEntity e = repository.findByModuleCode(code).orElseGet(() -> {
            ModuleRegistrationEntity n = new ModuleRegistrationEntity();
            n.setId(UUID.randomUUID().toString());
            n.setModuleCode(code);
            return n;
        });
        e.setModuleName(body.moduleName().trim());
        e.setOwnerCode(owner);
        e.setBaseUrl(blankToNull(body.baseUrl()));
        e.setHealthPath(blankToNull(body.healthPath()));
        e.setEnabled(body.enabled());
        e.setStatus(body.enabled() ? "REGISTERED" : "DISABLED");
        e.setContractVersion(body.contractVersion().trim());
        e.setUpdatedAt(OffsetDateTime.now());
        repository.save(e);
        audit.record(actor.id(), actor.getUsername(), "MODULE_UPSERT", "MODULE", code, "SUCCESS", null,
                jsons.write(Map.of("owner", owner)));
        return ModuleView.from(e);
    }

    private static void validateUrl(String value) {
        if (value == null || value.isBlank()) return;
        try {
            URI uri = URI.create(value);
            if (!("http".equalsIgnoreCase(uri.getScheme()) || "https".equalsIgnoreCase(uri.getScheme())) || uri.getHost() == null) {
                throw new IllegalArgumentException();
            }
        } catch (IllegalArgumentException ex) {
            throw new BusinessException(ErrorCode.INVALID_ARGUMENT, "baseUrl 必须是有效的 http/https 地址");
        }
    }
    private static String normalizeCode(String value) {
        String v = value.trim().toUpperCase();
        if (!v.matches("[A-Z0-9_-]{2,50}")) throw new BusinessException(ErrorCode.INVALID_ARGUMENT, "moduleCode 格式不正确");
        return v;
    }
    private static String blankToNull(String v) { return v == null || v.isBlank() ? null : v.trim(); }

    public record UpsertRequest(String moduleCode, String moduleName, String ownerCode, String baseUrl, String healthPath, boolean enabled, String contractVersion) {}
    public record ModuleView(String moduleCode, String moduleName, String ownerCode, String baseUrl, String healthPath, boolean enabled, String status, String contractVersion, OffsetDateTime lastCheckedAt, OffsetDateTime updatedAt) {
        static ModuleView from(ModuleRegistrationEntity e) {
            return new ModuleView(e.getModuleCode(), e.getModuleName(), e.getOwnerCode(), e.getBaseUrl(), e.getHealthPath(), e.isEnabled(), e.getStatus(), e.getContractVersion(), e.getLastCheckedAt(), e.getUpdatedAt());
        }
    }
}
