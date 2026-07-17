package com.xinji.foundation.module;

import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ModuleRegistrationRepository extends JpaRepository<ModuleRegistrationEntity, String> {
    Optional<ModuleRegistrationEntity> findByModuleCode(String moduleCode);
}
