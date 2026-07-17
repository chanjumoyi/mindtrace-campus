package com.xinji.foundation.module;

import jakarta.persistence.*;
import java.time.OffsetDateTime;

@Entity
@Table(name = "module_registration")
public class ModuleRegistrationEntity {
    @Id private String id;
    @Column(name = "module_code", nullable = false, unique = true) private String moduleCode;
    @Column(name = "module_name", nullable = false) private String moduleName;
    @Column(name = "owner_code", nullable = false) private String ownerCode;
    @Column(name = "base_url") private String baseUrl;
    @Column(name = "health_path") private String healthPath;
    @Column(nullable = false) private boolean enabled;
    @Column(nullable = false) private String status;
    @Column(name = "contract_version", nullable = false) private String contractVersion;
    @Column(name = "last_checked_at") private OffsetDateTime lastCheckedAt;
    @Column(name = "updated_at", nullable = false) private OffsetDateTime updatedAt;
    public String getId() { return id; } public void setId(String id) { this.id = id; }
    public String getModuleCode() { return moduleCode; } public void setModuleCode(String moduleCode) { this.moduleCode = moduleCode; }
    public String getModuleName() { return moduleName; } public void setModuleName(String moduleName) { this.moduleName = moduleName; }
    public String getOwnerCode() { return ownerCode; } public void setOwnerCode(String ownerCode) { this.ownerCode = ownerCode; }
    public String getBaseUrl() { return baseUrl; } public void setBaseUrl(String baseUrl) { this.baseUrl = baseUrl; }
    public String getHealthPath() { return healthPath; } public void setHealthPath(String healthPath) { this.healthPath = healthPath; }
    public boolean isEnabled() { return enabled; } public void setEnabled(boolean enabled) { this.enabled = enabled; }
    public String getStatus() { return status; } public void setStatus(String status) { this.status = status; }
    public String getContractVersion() { return contractVersion; } public void setContractVersion(String contractVersion) { this.contractVersion = contractVersion; }
    public OffsetDateTime getLastCheckedAt() { return lastCheckedAt; } public void setLastCheckedAt(OffsetDateTime lastCheckedAt) { this.lastCheckedAt = lastCheckedAt; }
    public OffsetDateTime getUpdatedAt() { return updatedAt; } public void setUpdatedAt(OffsetDateTime updatedAt) { this.updatedAt = updatedAt; }
}
