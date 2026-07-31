package com.xinji.foundation.analysis;

import com.xinji.foundation.common.ApiResponse;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import java.util.List;
import java.util.Map;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/analysis-records")
public class MultimodalAnalysisRecordController {
    private final MultimodalAnalysisRecordService service;

    public MultimodalAnalysisRecordController(MultimodalAnalysisRecordService service) {
        this.service = service;
    }

    @GetMapping
    @PreAuthorize("hasAuthority('task:read')")
    public ApiResponse<List<MultimodalAnalysisRecordService.AnalysisRecordView>> list(
            @RequestParam(required = false) AnalysisModuleType moduleType) {
        return ApiResponse.ok(service.list(moduleType));
    }

    @GetMapping("/{id}")
    @PreAuthorize("hasAuthority('task:read')")
    public ApiResponse<MultimodalAnalysisRecordService.AnalysisRecordView> get(@PathVariable String id) {
        return ApiResponse.ok(service.get(id));
    }

    @PostMapping
    @PreAuthorize("hasAuthority('task:write')")
    public ApiResponse<MultimodalAnalysisRecordService.AnalysisRecordView> create(
            @Valid @RequestBody CreateBody body) {
        var request = new MultimodalAnalysisRecordService.CreateAnalysisRecordRequest(
                body.moduleType(), body.taskId(), body.sourceRef(), body.title(), body.observations(),
                body.features(), body.aiSummary(), body.provider(), body.model(),
                Boolean.TRUE.equals(body.mockResult()));
        return ApiResponse.ok("分析记录已保存", service.create(request));
    }

    @DeleteMapping("/{id}")
    @PreAuthorize("hasAuthority('task:write')")
    public ApiResponse<Void> delete(@PathVariable String id) {
        service.delete(id);
        return ApiResponse.ok("分析记录已删除", null);
    }

    public record CreateBody(
            @NotNull AnalysisModuleType moduleType,
            @NotBlank @Size(max = 36) String taskId,
            @Size(max = 200) String sourceRef,
            @NotBlank @Size(max = 180) String title,
            @NotNull @Size(min = 1, max = 20) List<@NotBlank @Size(max = 500) String> observations,
            Map<String, Object> features,
            @Size(max = 5000) String aiSummary,
            @Size(max = 120) String provider,
            @Size(max = 120) String model,
            Boolean mockResult) {}
}
