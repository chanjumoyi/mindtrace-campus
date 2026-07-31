package com.xinji.foundation.plan;

import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ActionPlanRepository extends JpaRepository<ActionPlanEntity, String> {
    List<ActionPlanEntity> findTop50ByOwnerUserIdOrderByUpdatedAtDesc(String ownerUserId);
    List<ActionPlanEntity> findTop50ByOrderByUpdatedAtDesc();
    Optional<ActionPlanEntity> findByIdAndOwnerUserId(String id, String ownerUserId);
}
