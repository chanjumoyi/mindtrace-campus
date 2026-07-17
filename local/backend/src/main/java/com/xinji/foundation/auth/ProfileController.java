package com.xinji.foundation.auth;

import com.xinji.foundation.common.ApiResponse;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/me")
public class ProfileController {
    private final AuthService authService;
    public ProfileController(AuthService authService) { this.authService = authService; }
    @GetMapping
    @PreAuthorize("hasAuthority('profile:read')")
    public ApiResponse<AuthService.UserView> me() { return ApiResponse.ok(authService.me()); }
    @PatchMapping
    @PreAuthorize("hasAuthority('profile:write')")
    public ApiResponse<AuthService.UserView> update(@Valid @RequestBody UpdateProfileRequest body) {
        return ApiResponse.ok("个人资料已更新", authService.updateProfile(body.displayName(), body.email()));
    }
    public record UpdateProfileRequest(@NotBlank @Size(max = 100) String displayName, @Email @Size(max = 180) String email) {}
}
