package com.xinji.foundation.file;

import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface FileObjectRepository extends JpaRepository<FileObjectEntity, String> {
    List<FileObjectEntity> findTop100ByOwnerUserIdAndDeletedAtIsNullOrderByCreatedAtDesc(String ownerUserId);
    List<FileObjectEntity> findTop100ByDeletedAtIsNullOrderByCreatedAtDesc();
    Optional<FileObjectEntity> findByIdAndDeletedAtIsNull(String id);
}
