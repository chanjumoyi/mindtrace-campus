package com.xinji.foundation.analysis;

import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface MultimodalAnalysisRecordRepository extends JpaRepository<MultimodalAnalysisRecordEntity, String> {
    List<MultimodalAnalysisRecordEntity> findTop100ByDeletedAtIsNullOrderByCreatedAtDesc();
    List<MultimodalAnalysisRecordEntity> findTop100ByOwnerUserIdAndDeletedAtIsNullOrderByCreatedAtDesc(String ownerUserId);
    List<MultimodalAnalysisRecordEntity> findTop100ByOwnerUserIdAndModuleTypeAndDeletedAtIsNullOrderByCreatedAtDesc(
            String ownerUserId, AnalysisModuleType moduleType);
    List<MultimodalAnalysisRecordEntity> findTop100ByModuleTypeAndDeletedAtIsNullOrderByCreatedAtDesc(
            AnalysisModuleType moduleType);
    Optional<MultimodalAnalysisRecordEntity> findByIdAndDeletedAtIsNull(String id);
    Optional<MultimodalAnalysisRecordEntity> findByTaskIdAndDeletedAtIsNull(String taskId);
}
