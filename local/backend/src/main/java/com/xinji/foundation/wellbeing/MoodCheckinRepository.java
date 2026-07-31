package com.xinji.foundation.wellbeing;

import java.time.OffsetDateTime;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface MoodCheckinRepository extends JpaRepository<MoodCheckinEntity, String> {
    List<MoodCheckinEntity> findTop100ByOwnerUserIdAndOccurredAtGreaterThanEqualOrderByOccurredAtDesc(
            String ownerUserId, OffsetDateTime since);
    List<MoodCheckinEntity> findTop100ByOccurredAtGreaterThanEqualOrderByOccurredAtDesc(OffsetDateTime since);

    @Query(value = """
        SELECT CAST(m.occurred_at AS date) AS checkinDate, \
        ROUND(AVG(m.mood), 1) AS avgMood, \
        ROUND(AVG(m.stress), 1) AS avgStress, \
        ROUND(AVG(m.sleep_hours), 1) AS avgSleepHours, \
        COUNT(*) AS checkinCount \
        FROM mood_checkin m \
        WHERE m.owner_user_id = :userId AND m.occurred_at >= :since \
        GROUP BY CAST(m.occurred_at AS date) \
        ORDER BY CAST(m.occurred_at AS date) DESC\
        """, nativeQuery = true)
    List<Object[]> findDailyTrends(@Param("userId") String userId, @Param("since") OffsetDateTime since);
}
