package com.xinji.foundation.auth;

import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface RoleRepository extends JpaRepository<RoleEntity, String> {
    Optional<RoleEntity> findByCode(String code);
}
