package com.xinji.foundation.auth;

import jakarta.persistence.*;
import java.time.OffsetDateTime;
import java.util.LinkedHashSet;
import java.util.Set;

@Entity
@Table(name = "app_user")
public class UserEntity {
    @Id private String id;
    @Column(nullable = false, unique = true) private String username;
    @Column(name = "password_hash", nullable = false) private String passwordHash;
    @Column(name = "display_name", nullable = false) private String displayName;
    private String email;
    @Column(nullable = false) private String status;
    @Column(name = "created_at", nullable = false) private OffsetDateTime createdAt;
    @Column(name = "updated_at", nullable = false) private OffsetDateTime updatedAt;
    @ManyToMany(fetch = FetchType.EAGER)
    @JoinTable(name = "app_user_role", joinColumns = @JoinColumn(name = "user_id"), inverseJoinColumns = @JoinColumn(name = "role_id"))
    private Set<RoleEntity> roles = new LinkedHashSet<>();
    @Version private long version;
    public String getId() { return id; } public void setId(String id) { this.id = id; }
    public String getUsername() { return username; } public void setUsername(String username) { this.username = username; }
    public String getPasswordHash() { return passwordHash; } public void setPasswordHash(String passwordHash) { this.passwordHash = passwordHash; }
    public String getDisplayName() { return displayName; } public void setDisplayName(String displayName) { this.displayName = displayName; }
    public String getEmail() { return email; } public void setEmail(String email) { this.email = email; }
    public String getStatus() { return status; } public void setStatus(String status) { this.status = status; }
    public OffsetDateTime getCreatedAt() { return createdAt; } public void setCreatedAt(OffsetDateTime createdAt) { this.createdAt = createdAt; }
    public OffsetDateTime getUpdatedAt() { return updatedAt; } public void setUpdatedAt(OffsetDateTime updatedAt) { this.updatedAt = updatedAt; }
    public Set<RoleEntity> getRoles() { return roles; } public void setRoles(Set<RoleEntity> roles) { this.roles = roles; }
    public long getVersion() { return version; } public void setVersion(long version) { this.version = version; }
}
