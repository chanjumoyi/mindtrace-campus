package com.xinji.foundation.plan;

import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ActionPlanItemRepository extends JpaRepository<ActionPlanItemEntity, String> {
    Optional<ActionPlanItemEntity> findByIdAndPlanId(String id, String planId);
}
