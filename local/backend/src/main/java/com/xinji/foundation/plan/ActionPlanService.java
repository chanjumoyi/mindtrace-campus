package com.xinji.foundation.plan;

import com.xinji.foundation.audit.AuditService;
import com.xinji.foundation.auth.SecurityUtils;
import com.xinji.foundation.common.BusinessException;
import com.xinji.foundation.common.ErrorCode;
import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class ActionPlanService {
    private final ActionPlanRepository plans;
    private final ActionPlanItemRepository items;
    private final AuditService audit;

    public ActionPlanService(ActionPlanRepository plans, ActionPlanItemRepository items, AuditService audit) {
        this.plans = plans;
        this.items = items;
        this.audit = audit;
    }

    @Transactional
    public ActionPlanView create(CreateActionPlanRequest request) {
        var actor = SecurityUtils.current();
        OffsetDateTime now = OffsetDateTime.now();
        ActionPlanEntity plan = new ActionPlanEntity();
        plan.setId(UUID.randomUUID().toString());
        plan.setOwnerUserId(actor.id());
        plan.setTitle(request.title().trim());
        plan.setStatus("ACTIVE");
        plan.setCreatedAt(now);
        plan.setUpdatedAt(now);
        for (CreateActionItemRequest requestedItem : request.items()) {
            ActionPlanItemEntity item = new ActionPlanItemEntity();
            item.setId(UUID.randomUUID().toString());
            item.setTitle(requestedItem.title().trim());
            item.setScheduledOn(requestedItem.scheduledOn());
            item.setStatus("PENDING");
            item.setCreatedAt(now);
            plan.addItem(item);
        }
        plans.save(plan);
        audit.record(actor.id(), actor.getUsername(), "ACTION_PLAN_CREATE", "ACTION_PLAN",
                plan.getId(), "SUCCESS", null, null);
        return view(plan);
    }

    @Transactional(readOnly = true)
    public List<ActionPlanView> list(String ownerUserId) {
        var actor = SecurityUtils.current();
        boolean readAll = actor.permissions().contains("plan:read:all");
        String targetOwner = ownerUserId == null || ownerUserId.isBlank() ? actor.id() : ownerUserId.trim();
        List<ActionPlanEntity> visible = readAll && "*".equals(targetOwner)
                ? plans.findTop50ByOrderByUpdatedAtDesc()
                : plans.findTop50ByOwnerUserIdOrderByUpdatedAtDesc(readAll ? targetOwner : actor.id());
        return visible.stream().map(this::view).toList();
    }

    @Transactional
    public ActionPlanView updateItem(String planId, String itemId, UpdateActionItemRequest request) {
        var actor = SecurityUtils.current();
        ActionPlanEntity plan = plans.findByIdAndOwnerUserId(planId, actor.id())
                .orElseThrow(() -> new BusinessException(ErrorCode.NOT_FOUND, "行动计划不存在"));
        ActionPlanItemEntity item = items.findByIdAndPlanId(itemId, planId)
                .orElseThrow(() -> new BusinessException(ErrorCode.NOT_FOUND, "行动项不存在"));
        OffsetDateTime now = OffsetDateTime.now();
        item.setStatus(request.status());
        item.setFeedback(trimToNull(request.feedback()));
        item.setCompletedAt("DONE".equals(request.status()) ? now : null);
        item.setScheduledOn(request.scheduledOn() == null ? item.getScheduledOn() : request.scheduledOn());
        plan.setStatus(plan.getItems().stream().allMatch(candidate -> "DONE".equals(candidate.getStatus()))
                ? "COMPLETED" : "ACTIVE");
        plan.setUpdatedAt(now);
        plans.save(plan);
        audit.record(actor.id(), actor.getUsername(), "ACTION_PLAN_ITEM_UPDATE", "ACTION_PLAN",
                plan.getId(), "SUCCESS", null, null);
        return view(plan);
    }

    private ActionPlanView view(ActionPlanEntity plan) {
        return new ActionPlanView(plan.getId(), plan.getOwnerUserId(), plan.getTitle(), plan.getStatus(),
                plan.getItems().stream().map(item -> new ActionItemView(
                        item.getId(), item.getTitle(), item.getScheduledOn(), item.getStatus(),
                        item.getFeedback(), item.getCompletedAt())).toList(),
                plan.getCreatedAt(), plan.getUpdatedAt());
    }

    private static String trimToNull(String value) {
        return value == null || value.isBlank() ? null : value.trim();
    }

    public record CreateActionPlanRequest(String title, List<CreateActionItemRequest> items) {}
    public record CreateActionItemRequest(String title, LocalDate scheduledOn) {}
    public record UpdateActionItemRequest(String status, String feedback, LocalDate scheduledOn) {}
    public record ActionPlanView(String id, String ownerUserId, String title, String status,
                                 List<ActionItemView> items, OffsetDateTime createdAt, OffsetDateTime updatedAt) {}
    public record ActionItemView(String id, String title, LocalDate scheduledOn, String status,
                                 String feedback, OffsetDateTime completedAt) {}
}
