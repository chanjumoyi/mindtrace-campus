package com.xinji.foundation.plan;

import com.xinji.foundation.common.ApiResponse;
import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import java.time.LocalDate;
import java.util.List;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/action-plans")
public class ActionPlanController {
    private final ActionPlanService service;

    public ActionPlanController(ActionPlanService service) { this.service = service; }

    @GetMapping
    @PreAuthorize("hasAuthority('plan:read')")
    public ApiResponse<List<ActionPlanService.ActionPlanView>> list(
            @RequestParam(required = false) String ownerUserId) {
        return ApiResponse.ok(service.list(ownerUserId));
    }

    @PostMapping
    @PreAuthorize("hasAuthority('plan:write')")
    public ApiResponse<ActionPlanService.ActionPlanView> create(@Valid @RequestBody CreateBody body) {
        var request = new ActionPlanService.CreateActionPlanRequest(
                body.title(), body.items().stream()
                        .map(item -> new ActionPlanService.CreateActionItemRequest(item.title(), item.scheduledOn()))
                        .toList());
        return ApiResponse.ok("行动计划已创建", service.create(request));
    }

    @PatchMapping("/{planId}/items/{itemId}")
    @PreAuthorize("hasAuthority('plan:write')")
    public ApiResponse<ActionPlanService.ActionPlanView> updateItem(
            @PathVariable String planId, @PathVariable String itemId, @Valid @RequestBody UpdateItemBody body) {
        return ApiResponse.ok("行动项已更新", service.updateItem(planId, itemId,
                new ActionPlanService.UpdateActionItemRequest(body.status(), body.feedback(), body.scheduledOn())));
    }

    public record CreateBody(
            @NotBlank @Size(max = 120) String title,
            @NotNull @Size(min = 1, max = 8) List<@Valid CreateItemBody> items) {}
    public record CreateItemBody(
            @NotBlank @Size(max = 120) String title,
            @FutureOrPresent LocalDate scheduledOn) {}
    public record UpdateItemBody(
            @NotBlank @Pattern(regexp = "PENDING|DONE") String status,
            @Size(max = 280) String feedback,
            LocalDate scheduledOn) {}
}
