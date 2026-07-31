package com.xinji.foundation.wellbeing;

import com.xinji.foundation.common.ApiResponse;
import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import java.time.OffsetDateTime;
import java.util.List;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/mood-checkins")
public class MoodCheckinController {
    private final MoodCheckinService service;

    public MoodCheckinController(MoodCheckinService service) { this.service = service; }

    @GetMapping
    @PreAuthorize("hasAuthority('mood:read')")
    public ApiResponse<List<MoodCheckinService.MoodCheckinView>> list(
            @RequestParam(defaultValue = "14") @Min(1) @Max(90) int days,
            @RequestParam(required = false) String ownerUserId) {
        return ApiResponse.ok(service.list(days, ownerUserId));
    }

    @PostMapping
    @PreAuthorize("hasAuthority('mood:write')")
    public ApiResponse<MoodCheckinService.MoodCheckinView> create(@Valid @RequestBody CreateBody body) {
        var request = new MoodCheckinService.CreateMoodCheckinRequest(
                body.mood(), body.stress(), body.sleepHours(),
                body.tags() == null ? List.of() : body.tags(), body.occurredAt());
        return ApiResponse.ok("打卡已保存", service.create(request));
    }

    public record CreateBody(
            @Min(1) @Max(5) int mood,
            @Min(1) @Max(5) int stress,
            @DecimalMin("0.0") @DecimalMax("24.0") double sleepHours,
            @Size(max = 8) List<@NotBlank @Size(max = 20) String> tags,
            @PastOrPresent OffsetDateTime occurredAt) {}
}
