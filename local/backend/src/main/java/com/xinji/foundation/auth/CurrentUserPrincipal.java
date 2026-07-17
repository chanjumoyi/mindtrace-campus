package com.xinji.foundation.auth;

import java.util.Collections;
import java.util.LinkedHashSet;
import java.util.Set;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.userdetails.UserDetails;

public class CurrentUserPrincipal implements UserDetails {
    private final String id;
    private final String username;
    private final String displayName;
    private final Set<String> roles;
    private final Set<String> permissions;

    public CurrentUserPrincipal(UserEntity user) {
        this.id = user.getId();
        this.username = user.getUsername();
        this.displayName = user.getDisplayName();
        this.roles = new LinkedHashSet<>();
        this.permissions = new LinkedHashSet<>();
        user.getRoles().forEach(role -> {
            roles.add(role.getCode());
            role.getPermissions().forEach(p -> permissions.add(p.getCode()));
        });
    }
    public String id() { return id; }
    public String displayName() { return displayName; }
    public Set<String> roles() { return Collections.unmodifiableSet(roles); }
    public Set<String> permissions() { return Collections.unmodifiableSet(permissions); }
    @Override public java.util.Collection<? extends GrantedAuthority> getAuthorities() {
        Set<GrantedAuthority> result = new LinkedHashSet<>();
        roles.forEach(r -> result.add(new SimpleGrantedAuthority("ROLE_" + r)));
        permissions.forEach(p -> result.add(new SimpleGrantedAuthority(p)));
        return result;
    }
    @Override public String getPassword() { return ""; }
    @Override public String getUsername() { return username; }
}
