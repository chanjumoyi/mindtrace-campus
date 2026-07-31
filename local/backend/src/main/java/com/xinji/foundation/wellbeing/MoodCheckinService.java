package com.xinji.foundation.wellbeing;

import com.xinji.foundation.audit.AuditService;
import com.xinji.foundation.auth.SecurityUtils;
import com.xinji.foundation.common.Jsons;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class MoodCheckinService {
    private static final int MAX_DAYS = 90;
    private final MoodCheckinRepository repository;
    private final AuditService audit;
    private final Jsons jsons;

    public MoodCheckinService(MoodCheckinRepository repository, AuditService audit, Jsons jsons) {
        this.repository = repository;
        this.audit = audit;
        this.jsons = jsons;
    }

    @Transactional
    public MoodCheckinView create(CreateMoodCheckinRequest request) {
        var actor = SecurityUtils.current();
        OffsetDateTime now = OffsetDateTime.now();
        MoodCheckinEntity entity = new MoodCheckinEntity();
        entity.setId(UUID.randomUUID().toString());
        entity.setOwnerUserId(actor.id());
        entity.setMood(request.mood());
        entity.setStress(request.stress());
        entity.setSleepHours(request.sleepHours());
        entity.setTagsJson(jsons.write(request.tags() == null ? List.of() : request.tags()));
        entity.setOccurredAt(request.occurredAt() == null ? now : request.occurredAt());
        entity.setCreatedAt(now);
        repository.save(entity);
        audit.record(actor.id(), actor.getUsername(), "MOOD_CHECKIN_CREATE", "MOOD_CHECKIN",
                entity.getId(), "SUCCESS", null, null);
        return view(entity);
    }

    @Transactional(readOnly = true)
    public List<MoodCheckinView> list(int days, String ownerUserId) {
        var actor = SecurityUtils.current();
        int safeDays = Math.max(1, Math.min(days, MAX_DAYS));
        boolean readAll = actor.permissions().contains("mood:read:all");
        String targetOwner = ownerUserId == null || ownerUserId.isBlank() ? actor.id() : ownerUserId.trim();
        List<MoodCheckinEntity> records;
        if (readAll && "*".equals(targetOwner)) {
            records = repository.findTop100ByOccurredAtGreaterThanEqualOrderByOccurredAtDesc(
                    OffsetDateTime.now().minusDays(safeDays));
        } else {
            if (!readAll) targetOwner = actor.id();
            records = repository.findTop100ByOwnerUserIdAndOccurredAtGreaterThanEqualOrderByOccurredAtDesc(
                    targetOwner, OffsetDateTime.now().minusDays(safeDays));
        }
        return records.stream().map(this::view).toList();
    }

    private MoodCheckinView view(MoodCheckinEntity entity) {
        List<String> tags = List.of(jsons.read(entity.getTagsJson(), String[].class));
        return new MoodCheckinView(entity.getId(), entity.getOwnerUserId(), entity.getMood(), entity.getStress(),
                entity.getSleepHours(), tags, entity.getOccurredAt());
    }

    public record CreateMoodCheckinRequest(
            int mood, int stress, double sleepHours, List<String> tags, OffsetDateTime occurredAt) {}
    public record MoodCheckinView(
            String id, String ownerUserId, int mood, int stress, double sleepHours,
            List<String> tags, OffsetDateTime occurredAt) {}

}
