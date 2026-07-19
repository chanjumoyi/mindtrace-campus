package com.xinji.foundation.auth;

import com.xinji.foundation.config.XinjiProperties;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

@Component
public class TokenAuthenticationFilter extends OncePerRequestFilter {
    private final AuthService authService;
    private final XinjiProperties properties;

    public TokenAuthenticationFilter(AuthService authService, XinjiProperties properties) {
        this.authService = authService;
        this.properties = properties;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
            throws ServletException, IOException {
        String header = request.getHeader("Authorization");
        if (header != null && header.startsWith("Bearer ")
                && SecurityContextHolder.getContext().getAuthentication() == null) {
            String rawToken = header.substring(7).trim();
            CurrentUserPrincipal principal = authenticateService(rawToken);
            if (principal == null) principal = authService.authenticate(rawToken);
            if (principal != null) {
                UsernamePasswordAuthenticationToken authentication =
                        new UsernamePasswordAuthenticationToken(principal, null, principal.getAuthorities());
                SecurityContextHolder.getContext().setAuthentication(authentication);
            }
        }
        filterChain.doFilter(request, response);
    }

    private CurrentUserPrincipal authenticateService(String rawToken) {
        String configured = properties.getAuth().getServiceToken();
        if (configured == null || configured.isBlank() || rawToken == null || rawToken.isBlank()) return null;
        byte[] expected = configured.getBytes(StandardCharsets.UTF_8);
        byte[] actual = rawToken.getBytes(StandardCharsets.UTF_8);
        if (!MessageDigest.isEqual(expected, actual)) return null;
        return CurrentUserPrincipal.serviceAccount(
                properties.getAuth().getServiceAccountId(),
                properties.getAuth().getServiceAccountUsername(),
                properties.getAuth().getServiceAccountDisplayName(),
                properties.getAuth().getServicePermissions());
    }
}
