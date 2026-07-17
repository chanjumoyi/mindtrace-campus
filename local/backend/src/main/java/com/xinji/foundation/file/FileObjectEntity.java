package com.xinji.foundation.file;

import jakarta.persistence.*;
import java.time.OffsetDateTime;

@Entity
@Table(name = "file_object")
public class FileObjectEntity {
    @Id private String id;
    @Column(name = "owner_user_id", nullable = false) private String ownerUserId;
    @Column(name = "module_code", nullable = false) private String moduleCode;
    @Column(name = "original_name", nullable = false) private String originalName;
    @Column(name = "storage_name", nullable = false, unique = true) private String storageName;
    @Column(name = "content_type", nullable = false) private String contentType;
    @Column(name = "size_bytes", nullable = false) private long sizeBytes;
    @Column(nullable = false) private String sha256;
    @Column(name = "sensitivity_level", nullable = false) private String sensitivityLevel;
    @Column(name = "metadata_json", columnDefinition = "TEXT") private String metadataJson;
    @Column(name = "created_at", nullable = false) private OffsetDateTime createdAt;
    @Column(name = "deleted_at") private OffsetDateTime deletedAt;
    public String getId() { return id; } public void setId(String id) { this.id = id; }
    public String getOwnerUserId() { return ownerUserId; } public void setOwnerUserId(String ownerUserId) { this.ownerUserId = ownerUserId; }
    public String getModuleCode() { return moduleCode; } public void setModuleCode(String moduleCode) { this.moduleCode = moduleCode; }
    public String getOriginalName() { return originalName; } public void setOriginalName(String originalName) { this.originalName = originalName; }
    public String getStorageName() { return storageName; } public void setStorageName(String storageName) { this.storageName = storageName; }
    public String getContentType() { return contentType; } public void setContentType(String contentType) { this.contentType = contentType; }
    public long getSizeBytes() { return sizeBytes; } public void setSizeBytes(long sizeBytes) { this.sizeBytes = sizeBytes; }
    public String getSha256() { return sha256; } public void setSha256(String sha256) { this.sha256 = sha256; }
    public String getSensitivityLevel() { return sensitivityLevel; } public void setSensitivityLevel(String sensitivityLevel) { this.sensitivityLevel = sensitivityLevel; }
    public String getMetadataJson() { return metadataJson; } public void setMetadataJson(String metadataJson) { this.metadataJson = metadataJson; }
    public OffsetDateTime getCreatedAt() { return createdAt; } public void setCreatedAt(OffsetDateTime createdAt) { this.createdAt = createdAt; }
    public OffsetDateTime getDeletedAt() { return deletedAt; } public void setDeletedAt(OffsetDateTime deletedAt) { this.deletedAt = deletedAt; }
}
