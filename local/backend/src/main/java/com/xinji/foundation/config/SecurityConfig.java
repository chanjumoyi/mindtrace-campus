package com.xinji.foundation.config;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.xinji.foundation.auth.TokenAuthenticationFilter;
import com.xinji.foundation.common.ApiResponse;
import com.xinji.foundation.common.ErrorCode;
import jakarta.servlet.http.HttpServletResponse;
import java.util.List;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.MediaType;
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.CorsConfigurationSource;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;

@Configuration
@EnableMethodSecurity
public class SecurityConfig {
    @Bean
    PasswordEncoder passwordEncoder() { return new BCryptPasswordEncoder(12); }

    @Bean
    CorsConfigurationSource corsConfigurationSource(XinjiProperties properties) {
        CorsConfiguration cfg = new CorsConfiguration();
        cfg.setAllowedOrigins(properties.getCors().getAllowedOrigins());
        cfg.setAllowedMethods(List.of("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"));
        cfg.setAllowedHeaders(List.of("Authorization", "Content-Type", "Idempotency-Key", "X-Request-Id"));
        cfg.setExposedHeaders(List.of("X-Request-Id", "Content-Disposition"));
        cfg.setAllowCredentials(false);
        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/**", cfg);
        return source;
    }

    @Bean
    SecurityFilterChain securityFilterChain(HttpSecurity http, TokenAuthenticationFilter tokenFilter, ObjectMapper mapper) throws Exception {
        http.csrf(csrf -> csrf.disable())
                .cors(cors -> {})
                .sessionManagement(sm -> sm.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .authorizeHttpRequests(auth -> auth
                        .requestMatchers("/api/v1/auth/login", "/api/v1/public/**", "/actuator/health/**", "/error").permitAll()
                        .anyRequest().authenticated())
                .exceptionHandling(ex -> ex
                        .authenticationEntryPoint((req, res, e) -> write(res, mapper, 401, ErrorCode.UNAUTHORIZED, "请先登录或登录已过期"))
                        .accessDeniedHandler((req, res, e) -> write(res, mapper, 403, ErrorCode.FORBIDDEN, "没有访问该资源的权限")))
                .addFilterBefore(tokenFilter, UsernamePasswordAuthenticationFilter.class);
        return http.build();
    }

    private static void write(HttpServletResponse response, ObjectMapper mapper, int status, ErrorCode code, String message) throws java.io.IOException {
        response.setStatus(status);
        response.setContentType(MediaType.APPLICATION_JSON_VALUE);
        response.setCharacterEncoding("UTF-8");
        mapper.writeValue(response.getWriter(), ApiResponse.error(code.name(), message));
    }
}
