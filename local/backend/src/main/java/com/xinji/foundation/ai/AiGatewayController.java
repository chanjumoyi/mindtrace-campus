package com.xinji.foundation.ai;

import com.xinji.foundation.common.ApiResponse;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import java.util.List;
import java.util.Map;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/ai")
public class AiGatewayController {
    private final AiGatewayService service;
    public AiGatewayController(AiGatewayService service) { this.service = service; }
    @PostMapping("/invoke") @PreAuthorize("hasAuthority('ai:invoke')")
    public ApiResponse<AiGatewayService.InvokeResponse> invoke(@RequestHeader("Idempotency-Key") String key, @Valid @RequestBody InvokeBody body) {
        return ApiResponse.ok(service.invoke(key, new AiGatewayService.InvokeRequest(body.moduleCode(), body.operation(), body.input(), body.timeoutMs())));
    }
    @GetMapping("/call-logs") @PreAuthorize("hasAuthority('ai:log:read')")
    public ApiResponse<List<AiGatewayService.CallLogView>> logs() { return ApiResponse.ok(service.listLogs()); }
    public record InvokeBody(@NotBlank @Size(max=50) String moduleCode, @NotBlank @Size(max=100) String operation, Map<String,Object> input, Integer timeoutMs) {}
}
