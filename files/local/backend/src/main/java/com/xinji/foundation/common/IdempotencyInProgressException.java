package com.xinji.foundation.common;

public class IdempotencyInProgressException extends BusinessException {
    private final long retryAfterSeconds;

    public IdempotencyInProgressException(long retryAfterSeconds) {
        super(ErrorCode.IDEMPOTENCY_IN_PROGRESS, "相同请求正在处理中，请稍后重试");
        this.retryAfterSeconds = Math.max(1, retryAfterSeconds);
    }

    public long getRetryAfterSeconds() { return retryAfterSeconds; }
}
