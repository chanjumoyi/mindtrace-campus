package com.xinji.foundation.auth;

import jakarta.persistence.*;
import java.time.OffsetDateTime;
import java.util.LinkedHashSet;
import java.util.Set;

@Entity
@Table(name = "sys_role")
public class RoleEntity {
    @Id private String id;
    @Column(nullable = false, unique = true) private String code;
    @Column(nullable = false) private String name;
    @Column(name = "created_at", nullable = false) private OffsetDateTime createdAt;
    @ManyToMany(fetch = FetchType.EAGER)
    @JoinTable(name = "sys_role_permission", joinColumns = @JoinColumn(name = "role_id"), inverseJoinColumns = @JoinColumn(name = "permission_id"))
    private Set<PermissionEntity> permissions = new LinkedHashSet<>();
    public String getId() { return id; } public void setId(String id) { this.id = id; }
    public String getCode() { return code; } public void setCode(String code) { this.code = code; }
    public String getName() { return name; } public void setName(String name) { this.name = name; }
    public OffsetDateTime getCreatedAt() { return createdAt; } public void setCreatedAt(OffsetDateTime createdAt) { this.createdAt = createdAt; }
    public Set<PermissionEntity> getPermissions() { return permissions; } public void setPermissions(Set<PermissionEntity> permissions) { this.permissions = permissions; }
}
