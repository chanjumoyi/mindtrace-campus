package com.xinji.foundation.task;

import com.xinji.foundation.common.ApiResponse;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import java.util.List;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/tasks")
public class TaskController {
    private final TaskService service;
    public TaskController(TaskService service) { this.service = service; }
    @GetMapping @PreAuthorize("hasAuthority('task:read')")
    public ApiResponse<List<TaskService.TaskView>> list() { return ApiResponse.ok(service.list()); }
    @PostMapping @PreAuthorize("hasAuthority('task:write')")
    public ApiResponse<TaskService.TaskView> create(@Valid @RequestBody CreateBody body) {
        return ApiResponse.ok("任务已创建", service.create(new TaskService.CreateTaskRequest(body.moduleCode(), body.taskType(), body.title(), body.requestRef())));
    }
    @PatchMapping("/{id}/status") @PreAuthorize("hasAuthority('task:write')")
    public ApiResponse<TaskService.TaskView> transition(@PathVariable String id, @Valid @RequestBody TransitionBody body) {
        return ApiResponse.ok("任务状态已更新", service.transition(id, new TaskService.TransitionRequest(body.status(), body.progress(), body.resultRef(), body.errorCode(), body.errorMessage())));
    }
    public record CreateBody(@NotBlank @Size(max=50) String moduleCode, @NotBlank @Size(max=80) String taskType, @NotBlank @Size(max=180) String title, @Size(max=200) String requestRef) {}
    public record TransitionBody(@NotNull TaskStatus status, Integer progress, @Size(max=200) String resultRef, @Size(max=80) String errorCode, @Size(max=500) String errorMessage) {}
}
