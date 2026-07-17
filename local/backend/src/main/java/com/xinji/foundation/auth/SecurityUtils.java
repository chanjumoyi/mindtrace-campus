package com.xinji.foundation.auth;

import com.xinji.foundation.common.BusinessException;
import com.xinji.foundation.common.ErrorCode;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;

public final class SecurityUtils {
    private SecurityUtils() {}
    public static CurrentUserPrincipal current() {
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        if (auth == null || !(auth.getPrincipal() instanceof CurrentUserPrincipal principal)) {
            throw new BusinessException(ErrorCode.UNAUTHORIZED, "请先登录");
        }
        return principal;
    }
}
