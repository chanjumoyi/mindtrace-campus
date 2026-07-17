package com.xinji.foundation.ai;

import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface AiCallLogRepository extends JpaRepository<AiCallLogEntity, String> {
    List<AiCallLogEntity> findTop100ByActorUserIdOrderByCreatedAtDesc(String actorUserId);
    List<AiCallLogEntity> findTop100ByOrderByCreatedAtDesc();
}
