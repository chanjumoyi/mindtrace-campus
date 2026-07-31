package com.xinji.foundation.safety;

import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;

public interface RiskSignalRepository extends JpaRepository<RiskSignalEntity, String> {
    List<RiskSignalEntity> findTop50ByUserIdOrderByCreatedAtDesc(String userId);
    List<RiskSignalEntity> findByLevelOrderByCreatedAtDesc(String level);
}
