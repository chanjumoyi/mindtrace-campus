package com.xinji.foundation.task;

import com.xinji.foundation.audit.AuditService;
import com.xinji.foundation.auth.SecurityUtils;
import com.xinji.foundation.common.BusinessException;
import com.xinji.foundation.common.ErrorCode;
import com.xinji.foundation.common.Jsons;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class TaskService {
    private static final Map<TaskStatus, Set<TaskStatus>> TRANSITIONS = Map.of(
        TaskStatus.PENDING, Set.of(TaskStatus.RUNNING, TaskStatus.CANCELLED, TaskStatus.FAILED),
        TaskStatus.RUNNING, Set.of(TaskStatus.SUCCEEDED, TaskStatus.FAILED, TaskStatus.CANCELLED),
        TaskStatus.SUCCEEDED, Set.of(),
        TaskStatus.FAILED, Set.of(TaskStatus.PENDING),
        TaskStatus.CANCELLED, Set.of(TaskStatus.PENDING)
    );
    private final TaskRepository repository;
    private final AuditService audit;
    private final Jsons jsons;
    public TaskService(TaskRepository repository, AuditService audit, Jsons jsons) {
        this.repository = repository; this.audit = audit; this.jsons = jsons;
    }

    @Transactional
    public TaskView create(CreateTaskRequest body) {
        var actor = SecurityUtils.current();
        TaskEntity e = new TaskEntity();
        e.setId(UUID.randomUUID().toString());
        e.setOwnerUserId(actor.id());
        e.setModuleCode(normalizeModule(body.moduleCode()));
        e.setTaskType(body.taskType().trim());
        e.setTitle(body.title().trim());
        e.setStatus(TaskStatus.PENDING);
        e.setProgress(0);
        e.setRequestRef(body.requestRef());
        e.setCreatedAt(OffsetDateTime.now());
        e.setUpdatedAt(e.getCreatedAt());
        repository.save(e);
        audit.record(actor.id(), actor.getUsername(), "TASK_CREATE", "TASK", e.getId(), "SUCCESS", null,
                jsons.write(Map.of("module", e.getModuleCode())));
        return TaskView.from(e);
    }

    @Transactional(readOnly = true)
    public List<TaskView> list() {
        var actor = SecurityUtils.current();
        List<TaskEntity> rows = actor.permissions().contains("task:read:all")
                ? repository.findTop100ByOrderByCreatedAtDesc()
                : repository.findTop100ByOwnerUserIdOrderByCreatedAtDesc(actor.id());
        return rows.stream().map(TaskView::from).toList();
    }

    @Transactional
    public TaskView transition(String id, TransitionRequest body) {
        var actor = SecurityUtils.current();
        TaskEntity e = repository.findById(id).orElseThrow(() -> new BusinessException(ErrorCode.NOT_FOUND, "任务不存在"));
        ensureVisible(e, actor.id(), actor.permissions().contains("task:write:all"));
        TaskStatus target = body.status();
        if (!TRANSITIONS.getOrDefault(e.getStatus(), Set.of()).contains(target)) {
            throw new BusinessException(ErrorCode.INVALID_STATE_TRANSITION, "不允许从 " + e.getStatus() + " 切换到 " + target);
        }
        e.setStatus(target);
        e.setProgress(target == TaskStatus.SUCCEEDED ? 100 : Math.max(0, Math.min(body.progress() == null ? e.getProgress() : body.progress(), 100)));
        e.setResultRef(body.resultRef());
        e.setErrorCode(body.errorCode());
        e.setErrorMessage(safe(body.errorMessage(), 500));
        e.setUpdatedAt(OffsetDateTime.now());
        repository.save(e);
        audit.record(actor.id(), actor.getUsername(), "TASK_TRANSITION", "TASK", e.getId(), "SUCCESS", null,
                jsons.write(Map.of("status", target.name())));
        return TaskView.from(e);
    }

    private static void ensureVisible(TaskEntity e, String actorId, boolean all) {
        if (!all && !actorId.equals(e.getOwnerUserId())) throw new BusinessException(ErrorCode.FORBIDDEN, "无权操作该任务");
    }
    private static String normalizeModule(String value) {
        String v = value.trim().toUpperCase();
        if (!v.matches("[A-Z0-9_-]{2,50}")) throw new BusinessException(ErrorCode.INVALID_ARGUMENT, "moduleCode 格式不正确");
        return v;
    }
    private static String safe(String value, int max) { return value == null ? null : value.substring(0, Math.min(value.length(), max)); }

    public record CreateTaskRequest(String moduleCode, String taskType, String title, String requestRef) {}
    public record TransitionRequest(TaskStatus status, Integer progress, String resultRef, String errorCode, String errorMessage) {}
    public record TaskView(String id, String ownerUserId, String moduleCode, String taskType, String title, TaskStatus status, int progress, String requestRef, String resultRef, String errorCode, String errorMessage, long version, OffsetDateTime createdAt, OffsetDateTime updatedAt) {
        static TaskView from(TaskEntity e) {
            return new TaskView(e.getId(), e.getOwnerUserId(), e.getModuleCode(), e.getTaskType(), e.getTitle(), e.getStatus(), e.getProgress(), e.getRequestRef(), e.getResultRef(), e.getErrorCode(), e.getErrorMessage(), e.getVersion(), e.getCreatedAt(), e.getUpdatedAt());
        }
    }
}
