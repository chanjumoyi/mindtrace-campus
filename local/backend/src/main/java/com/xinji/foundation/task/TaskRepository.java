package com.xinji.foundation.task;

import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface TaskRepository extends JpaRepository<TaskEntity, String> {
    List<TaskEntity> findTop100ByOwnerUserIdOrderByCreatedAtDesc(String ownerUserId);
    List<TaskEntity> findTop100ByOrderByCreatedAtDesc();
}
