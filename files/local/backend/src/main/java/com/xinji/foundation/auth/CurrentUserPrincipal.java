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
        this(user.getId(), user.getUsername(), user.getDisplayName(), new LinkedHashSet<>(), new LinkedHashSet<>());
        user.getRoles().forEach(role -> {
            roles.add(role.getCode());
            role.getPermissions().forEach(p -> permissions.add(p.getCode()));
        });
    }

    private CurrentUserPrincipal(String id, String username, String displayName, Set<String> roles, Set<String> permissions) {
        this.id = id;
        this.username = username;
        this.displayName = displayName;
        this.roles = roles;
        this.permissions = permissions;
    }

    public static CurrentUserPrincipal serviceAccount(String id, String username, String displayName, java.util.Collection<String> permissions) {
        return new CurrentUserPrincipal(id, username, displayName,
                new LinkedHashSet<>(Set.of("SERVICE")), new LinkedHashSet<>(permissions));
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
