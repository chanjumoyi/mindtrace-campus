package com.xinji.foundation.ai;

import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface AiCallAttemptLogRepository extends JpaRepository<AiCallAttemptLogEntity, String> {
    List<AiCallAttemptLogEntity> findByCallIdOrderByAttemptNo(String callId);
}
