package com.xinji.foundation.module;

import com.xinji.foundation.common.ApiResponse;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import java.util.List;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/modules")
public class ModuleRegistryController {
    private final ModuleRegistryService service;
    public ModuleRegistryController(ModuleRegistryService service) { this.service = service; }
    @GetMapping @PreAuthorize("hasAuthority('module:read')")
    public ApiResponse<List<ModuleRegistryService.ModuleView>> list() { return ApiResponse.ok(service.list()); }
    @PutMapping("/{moduleCode}") @PreAuthorize("hasAuthority('module:write')")
    public ApiResponse<ModuleRegistryService.ModuleView> upsert(@PathVariable String moduleCode, @Valid @RequestBody Body body) {
        return ApiResponse.ok("模块注册信息已保存", service.upsert(new ModuleRegistryService.UpsertRequest(moduleCode, body.moduleName(), body.ownerCode(), body.baseUrl(), body.healthPath(), body.enabled(), body.contractVersion())));
    }
    public record Body(@NotBlank @Size(max=120) String moduleName, @NotBlank @Size(max=10) String ownerCode, @Size(max=500) String baseUrl, @Size(max=200) String healthPath, boolean enabled, @NotBlank @Size(max=30) String contractVersion) {}
}
