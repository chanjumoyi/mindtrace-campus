package com.xinji.foundation.common;

import java.time.OffsetDateTime;

public record ApiResponse<T>(boolean success, String code, String message, T data, String requestId, OffsetDateTime timestamp) {
    public static <T> ApiResponse<T> ok(T data) {
        return new ApiResponse<>(true, "OK", "success", data, RequestContext.requestId(), OffsetDateTime.now());
    }
    public static <T> ApiResponse<T> ok(String message, T data) {
        return new ApiResponse<>(true, "OK", message, data, RequestContext.requestId(), OffsetDateTime.now());
    }
    public static ApiResponse<Void> error(String code, String message) {
        return new ApiResponse<>(false, code, message, null, RequestContext.requestId(), OffsetDateTime.now());
    }
}
