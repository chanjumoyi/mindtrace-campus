package com.xinji.foundation.audit;

import com.xinji.foundation.common.ApiResponse;
import org.springframework.data.domain.Page;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/audit-logs")
public class AuditController {
    private final AuditService service;
    public AuditController(AuditService service) { this.service = service; }
    @GetMapping
    @PreAuthorize("hasAuthority('audit:read')")
    public ApiResponse<Page<AuditService.AuditView>> list(@RequestParam(defaultValue = "0") int page, @RequestParam(defaultValue = "20") int size) {
        return ApiResponse.ok(service.list(page, size));
    }
}
