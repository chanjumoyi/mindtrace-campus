package com.xinji.foundation.wellbeing;

import java.time.OffsetDateTime;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface MoodCheckinRepository extends JpaRepository<MoodCheckinEntity, String> {
    List<MoodCheckinEntity> findTop100ByOwnerUserIdAndOccurredAtGreaterThanEqualOrderByOccurredAtDesc(
            String ownerUserId, OffsetDateTime since);
    List<MoodCheckinEntity> findTop100ByOccurredAtGreaterThanEqualOrderByOccurredAtDesc(OffsetDateTime since);
}
