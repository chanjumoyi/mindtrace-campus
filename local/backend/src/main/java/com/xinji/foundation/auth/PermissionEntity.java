package com.xinji.foundation.auth;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.OffsetDateTime;

@Entity
@Table(name = "sys_permission")
public class PermissionEntity {
    @Id private String id;
    @Column(nullable = false, unique = true) private String code;
    @Column(nullable = false) private String name;
    @Column(name = "created_at", nullable = false) private OffsetDateTime createdAt;
    public String getId() { return id; } public void setId(String id) { this.id = id; }
    public String getCode() { return code; } public void setCode(String code) { this.code = code; }
    public String getName() { return name; } public void setName(String name) { this.name = name; }
    public OffsetDateTime getCreatedAt() { return createdAt; } public void setCreatedAt(OffsetDateTime createdAt) { this.createdAt = createdAt; }
}
