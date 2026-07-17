package com.xinji.foundation.common;

import org.springframework.http.HttpStatus;

public enum ErrorCode {
    INVALID_ARGUMENT(HttpStatus.BAD_REQUEST),
    UNAUTHORIZED(HttpStatus.UNAUTHORIZED),
    FORBIDDEN(HttpStatus.FORBIDDEN),
    NOT_FOUND(HttpStatus.NOT_FOUND),
    CONFLICT(HttpStatus.CONFLICT),
    IDEMPOTENCY_CONFLICT(HttpStatus.CONFLICT),
    INVALID_STATE_TRANSITION(HttpStatus.CONFLICT),
    FILE_TYPE_NOT_ALLOWED(HttpStatus.UNSUPPORTED_MEDIA_TYPE),
    FILE_TOO_LARGE(HttpStatus.PAYLOAD_TOO_LARGE),
    AGENT_TIMEOUT(HttpStatus.GATEWAY_TIMEOUT),
    AGENT_UNAVAILABLE(HttpStatus.BAD_GATEWAY),
    RATE_LIMITED(HttpStatus.TOO_MANY_REQUESTS),
    INTERNAL_ERROR(HttpStatus.INTERNAL_SERVER_ERROR);

    private final HttpStatus status;
    ErrorCode(HttpStatus status) { this.status = status; }
    public HttpStatus status() { return status; }
}
