package com.xinji.foundation.auth;

import com.xinji.foundation.audit.AuditService;
import com.xinji.foundation.common.BusinessException;
import com.xinji.foundation.common.ErrorCode;
import com.xinji.foundation.common.Hashes;
import com.xinji.foundation.config.XinjiProperties;
import java.security.SecureRandom;
import java.time.OffsetDateTime;
import java.util.Base64;
import java.util.UUID;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class AuthService {
    private final UserRepository users;
    private final AuthSessionRepository sessions;
    private final PasswordEncoder passwordEncoder;
    private final XinjiProperties properties;
    private final AuditService audit;
    private final SecureRandom random = new SecureRandom();

    public AuthService(UserRepository users, AuthSessionRepository sessions, PasswordEncoder passwordEncoder, XinjiProperties properties, AuditService audit) {
        this.users = users; this.sessions = sessions; this.passwordEncoder = passwordEncoder; this.properties = properties; this.audit = audit;
    }

    @Transactional
    public LoginResult login(String username, String password, String ip) {
        UserEntity user = users.findByUsername(username).orElseThrow(() -> new BusinessException(ErrorCode.UNAUTHORIZED, "用户名或密码错误"));
        if (!"ACTIVE".equals(user.getStatus()) || !passwordEncoder.matches(password, user.getPasswordHash())) {
            audit.record(null, username, "AUTH_LOGIN", "USER", user.getId(), "FAILED", ip, null);
            throw new BusinessException(ErrorCode.UNAUTHORIZED, "用户名或密码错误");
        }
        byte[] bytes = new byte[32]; random.nextBytes(bytes);
        String rawToken = Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
        OffsetDateTime now = OffsetDateTime.now();
        AuthSessionEntity session = new AuthSessionEntity();
        session.setId(UUID.randomUUID().toString());
        session.setUserId(user.getId());
        session.setTokenHash(Hashes.sha256(rawToken));
        session.setCreatedAt(now);
        session.setExpiresAt(now.plusHours(properties.getAuth().getTokenTtlHours()));
        sessions.save(session);
        audit.record(user.getId(), user.getUsername(), "AUTH_LOGIN", "USER", user.getId(), "SUCCESS", ip, null);
        return new LoginResult(rawToken, session.getExpiresAt(), toView(user));
    }

    @Transactional(readOnly = true)
    public CurrentUserPrincipal authenticate(String rawToken) {
        if (rawToken == null || rawToken.isBlank()) return null;
        return sessions.findByTokenHashAndRevokedAtIsNullAndExpiresAtAfter(Hashes.sha256(rawToken), OffsetDateTime.now())
                .flatMap(s -> users.findById(s.getUserId()))
                .filter(u -> "ACTIVE".equals(u.getStatus()))
                .map(CurrentUserPrincipal::new).orElse(null);
    }

    @Transactional
    public void logout(String rawToken, String ip) {
        if (rawToken == null || rawToken.isBlank()) return;
        sessions.findByTokenHashAndRevokedAtIsNullAndExpiresAtAfter(Hashes.sha256(rawToken), OffsetDateTime.now()).ifPresent(session -> {
            session.setRevokedAt(OffsetDateTime.now());
            sessions.save(session);
            users.findById(session.getUserId()).ifPresent(u -> audit.record(u.getId(), u.getUsername(), "AUTH_LOGOUT", "USER", u.getId(), "SUCCESS", ip, null));
        });
    }

    @Transactional(readOnly = true)
    public UserView me() {
        UserEntity user = users.findById(SecurityUtils.current().id()).orElseThrow(() -> new BusinessException(ErrorCode.NOT_FOUND, "用户不存在"));
        return toView(user);
    }

    @Transactional
    public UserView updateProfile(String displayName, String email) {
        UserEntity user = users.findById(SecurityUtils.current().id()).orElseThrow(() -> new BusinessException(ErrorCode.NOT_FOUND, "用户不存在"));
        user.setDisplayName(displayName.trim());
        user.setEmail(email == null || email.isBlank() ? null : email.trim());
        user.setUpdatedAt(OffsetDateTime.now());
        users.save(user);
        audit.record(user.getId(), user.getUsername(), "PROFILE_UPDATE", "USER", user.getId(), "SUCCESS", null, null);
        return toView(user);
    }

    public static UserView toView(UserEntity user) {
        CurrentUserPrincipal p = new CurrentUserPrincipal(user);
        return new UserView(user.getId(), user.getUsername(), user.getDisplayName(), user.getEmail(), p.roles(), p.permissions());
    }

    public record LoginResult(String accessToken, OffsetDateTime expiresAt, UserView user) {}
    public record UserView(String id, String username, String displayName, String email, java.util.Set<String> roles, java.util.Set<String> permissions) {}
}
