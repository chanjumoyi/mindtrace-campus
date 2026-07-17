package com.xinji.foundation.common;

import jakarta.validation.ConstraintViolationException;
import java.util.stream.Collectors;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public class GlobalExceptionHandler {
    private static final Logger log = LoggerFactory.getLogger(GlobalExceptionHandler.class);

    @ExceptionHandler(BusinessException.class)
    ResponseEntity<ApiResponse<Void>> business(BusinessException ex) {
        return ResponseEntity.status(ex.getErrorCode().status()).body(ApiResponse.error(ex.getErrorCode().name(), ex.getMessage()));
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    ResponseEntity<ApiResponse<Void>> validation(MethodArgumentNotValidException ex) {
        String message = ex.getBindingResult().getFieldErrors().stream()
                .map(e -> e.getField() + ": " + e.getDefaultMessage()).collect(Collectors.joining("; "));
        return ResponseEntity.badRequest().body(ApiResponse.error(ErrorCode.INVALID_ARGUMENT.name(), message));
    }

    @ExceptionHandler(ConstraintViolationException.class)
    ResponseEntity<ApiResponse<Void>> constraint(ConstraintViolationException ex) {
        return ResponseEntity.badRequest().body(ApiResponse.error(ErrorCode.INVALID_ARGUMENT.name(), ex.getMessage()));
    }

    @ExceptionHandler(AccessDeniedException.class)
    ResponseEntity<ApiResponse<Void>> denied(AccessDeniedException ex) {
        return ResponseEntity.status(403).body(ApiResponse.error(ErrorCode.FORBIDDEN.name(), "没有访问该资源的权限"));
    }

    @ExceptionHandler(DataIntegrityViolationException.class)
    ResponseEntity<ApiResponse<Void>> conflict(DataIntegrityViolationException ex) {
        return ResponseEntity.status(409).body(ApiResponse.error(ErrorCode.CONFLICT.name(), "数据冲突，请刷新后重试"));
    }

    @ExceptionHandler(Exception.class)
    ResponseEntity<ApiResponse<Void>> unknown(Exception ex) {
        log.error("Unhandled error", ex);
        return ResponseEntity.status(500).body(ApiResponse.error(ErrorCode.INTERNAL_ERROR.name(), "系统内部错误，请凭 requestId 联系管理员"));
    }
}
