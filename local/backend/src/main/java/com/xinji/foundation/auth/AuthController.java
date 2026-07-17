package com.xinji.foundation.auth;

import com.xinji.foundation.common.ApiResponse;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/auth")
public class AuthController {
    private final AuthService authService;
    public AuthController(AuthService authService) { this.authService = authService; }

    @PostMapping("/login")
    public ApiResponse<AuthService.LoginResult> login(@Valid @RequestBody LoginRequest body, HttpServletRequest request) {
        return ApiResponse.ok("登录成功", authService.login(body.username(), body.password(), clientIp(request)));
    }

    @PostMapping("/logout")
    public ApiResponse<Void> logout(@RequestHeader(value = "Authorization", required = false) String authorization, HttpServletRequest request) {
        String token = authorization != null && authorization.startsWith("Bearer ") ? authorization.substring(7).trim() : null;
        authService.logout(token, clientIp(request));
        return ApiResponse.ok("已退出登录", null);
    }

    private static String clientIp(HttpServletRequest request) {
        String forwarded = request.getHeader("X-Forwarded-For");
        return forwarded == null || forwarded.isBlank() ? request.getRemoteAddr() : forwarded.split(",")[0].trim();
    }

    public record LoginRequest(@NotBlank @Size(max = 80) String username, @NotBlank @Size(max = 128) String password) {}
}
