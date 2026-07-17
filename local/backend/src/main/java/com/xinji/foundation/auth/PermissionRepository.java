package com.xinji.foundation.auth;

import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface PermissionRepository extends JpaRepository<PermissionEntity, String> {
    Optional<PermissionEntity> findByCode(String code);
}
