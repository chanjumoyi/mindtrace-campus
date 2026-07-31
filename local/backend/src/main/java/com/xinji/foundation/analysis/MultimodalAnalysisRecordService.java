package com.xinji.foundation.analysis;

import com.xinji.foundation.audit.AuditService;
import com.xinji.foundation.auth.SecurityUtils;
import com.xinji.foundation.common.BusinessException;
import com.xinji.foundation.common.ErrorCode;
import com.xinji.foundation.common.Jsons;
import com.xinji.foundation.task.TaskRepository;
import com.xinji.foundation.task.TaskStatus;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class MultimodalAnalysisRecordService {
    private static final int MAX_PAYLOAD_JSON_LENGTH = 20_000;

    private final MultimodalAnalysisRecordRepository repository;
    private final TaskRepository tasks;
    private final AuditService audit;
    private final Jsons jsons;

    public MultimodalAnalysisRecordService(
            MultimodalAnalysisRecordRepository repository,
            TaskRepository tasks,
            AuditService audit,
            Jsons jsons) {
        this.repository = repository;
        this.tasks = tasks;
        this.audit = audit;
        this.jsons = jsons;
    }

    @Transactional
    public AnalysisRecordView create(CreateAnalysisRecordRequest body) {
        var actor = SecurityUtils.current();
        var task = tasks.findById(body.taskId())
                .orElseThrow(() -> new BusinessException(ErrorCode.NOT_FOUND, "关联任务不存在"));
        boolean canWriteAll = actor.permissions().contains("task:write:all");
        if (!canWriteAll && !actor.id().equals(task.getOwnerUserId())) {
            throw new BusinessException(ErrorCode.FORBIDDEN, "无权为该任务保存分析记录");
        }
        if (task.getStatus() != TaskStatus.RUNNING) {
            throw new BusinessException(ErrorCode.INVALID_STATE_TRANSITION, "只有运行中的任务可以保存分析记录");
        }

        var existing = repository.findByTaskIdAndDeletedAtIsNull(body.taskId());
        if (existing.isPresent()) return view(existing.get());

        StoredObservation stored = new StoredObservation(
                List.copyOf(body.observations()),
                body.features() == null ? Map.of() : Map.copyOf(body.features()));
        String observationJson = jsons.write(stored);
        if (observationJson.length() > MAX_PAYLOAD_JSON_LENGTH) {
            throw new BusinessException(ErrorCode.INVALID_ARGUMENT, "结构化观察数据过大");
        }

        MultimodalAnalysisRecordEntity entity = new MultimodalAnalysisRecordEntity();
        entity.setId(UUID.randomUUID().toString());
        entity.setOwnerUserId(task.getOwnerUserId());
        entity.setModuleType(body.moduleType());
        entity.setTaskId(task.getId());
        entity.setSourceRef(trimToNull(body.sourceRef()));
        entity.setTitle(body.title().trim());
        entity.setObservationJson(observationJson);
        entity.setAiSummary(trimToNull(body.aiSummary()));
        entity.setProvider(trimToNull(body.provider()));
        entity.setModel(trimToNull(body.model()));
        entity.setMockResult(body.mockResult());
        entity.setCreatedAt(OffsetDateTime.now());
        repository.save(entity);

        audit.record(actor.id(), actor.getUsername(), "ANALYSIS_RECORD_CREATE", "ANALYSIS_RECORD",
                entity.getId(), "SUCCESS", null,
                jsons.write(Map.of(
                        "moduleType", entity.getModuleType().name(),
                        "taskId", entity.getTaskId(),
                        "provider", entity.getProvider() == null ? "unknown" : entity.getProvider(),
                        "mock", entity.isMockResult())));
        return view(entity);
    }

    @Transactional(readOnly = true)
    public List<AnalysisRecordView> list(AnalysisModuleType moduleType) {
        var actor = SecurityUtils.current();
        boolean readAll = actor.permissions().contains("task:read:all");
        List<MultimodalAnalysisRecordEntity> records;
        if (readAll) {
            records = moduleType == null
                    ? repository.findTop100ByDeletedAtIsNullOrderByCreatedAtDesc()
                    : repository.findTop100ByModuleTypeAndDeletedAtIsNullOrderByCreatedAtDesc(moduleType);
        } else {
            records = moduleType == null
                    ? repository.findTop100ByOwnerUserIdAndDeletedAtIsNullOrderByCreatedAtDesc(actor.id())
                    : repository.findTop100ByOwnerUserIdAndModuleTypeAndDeletedAtIsNullOrderByCreatedAtDesc(
                            actor.id(), moduleType);
        }
        return records.stream().map(this::view).toList();
    }

    @Transactional(readOnly = true)
    public AnalysisRecordView get(String id) {
        MultimodalAnalysisRecordEntity entity = repository.findByIdAndDeletedAtIsNull(id)
                .orElseThrow(() -> new BusinessException(ErrorCode.NOT_FOUND, "分析记录不存在"));
        ensureReadable(entity);
        return view(entity);
    }

    @Transactional
    public void delete(String id) {
        var actor = SecurityUtils.current();
        MultimodalAnalysisRecordEntity entity = repository.findByIdAndDeletedAtIsNull(id)
                .orElseThrow(() -> new BusinessException(ErrorCode.NOT_FOUND, "分析记录不存在"));
        boolean writeAll = actor.permissions().contains("task:write:all");
        if (!writeAll && !actor.id().equals(entity.getOwnerUserId())) {
            throw new BusinessException(ErrorCode.FORBIDDEN, "无权删除该分析记录");
        }
        repository.delete(entity);
        audit.record(actor.id(), actor.getUsername(), "ANALYSIS_RECORD_DELETE", "ANALYSIS_RECORD",
                entity.getId(), "SUCCESS", null, null);
    }

    private void ensureReadable(MultimodalAnalysisRecordEntity entity) {
        var actor = SecurityUtils.current();
        if (!actor.permissions().contains("task:read:all") && !actor.id().equals(entity.getOwnerUserId())) {
            throw new BusinessException(ErrorCode.FORBIDDEN, "无权读取该分析记录");
        }
    }

    private AnalysisRecordView view(MultimodalAnalysisRecordEntity entity) {
        StoredObservation stored = jsons.read(entity.getObservationJson(), StoredObservation.class);
        return new AnalysisRecordView(
                entity.getId(), entity.getOwnerUserId(), entity.getModuleType(), entity.getTaskId(),
                entity.getSourceRef(), entity.getTitle(), stored.observations(), stored.features(),
                entity.getAiSummary(), entity.getProvider(), entity.getModel(), entity.isMockResult(),
                entity.getCreatedAt());
    }

    private static String trimToNull(String value) {
        if (value == null || value.isBlank()) return null;
        return value.trim();
    }

    public record CreateAnalysisRecordRequest(
            AnalysisModuleType moduleType,
            String taskId,
            String sourceRef,
            String title,
            List<String> observations,
            Map<String, Object> features,
            String aiSummary,
            String provider,
            String model,
            boolean mockResult) {}

    public record AnalysisRecordView(
            String id,
            String ownerUserId,
            AnalysisModuleType moduleType,
            String taskId,
            String sourceRef,
            String title,
            List<String> observations,
            Map<String, Object> features,
            String aiSummary,
            String provider,
            String model,
            boolean mockResult,
            OffsetDateTime createdAt) {}

    public record StoredObservation(List<String> observations, Map<String, Object> features) {}
}
