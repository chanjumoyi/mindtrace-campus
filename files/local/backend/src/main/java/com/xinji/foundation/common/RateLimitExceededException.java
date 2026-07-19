package com.xinji.foundation.common;

public class RateLimitExceededException extends BusinessException {
    private final long retryAfterSeconds;
    private final int limit;

    public RateLimitExceededException(long retryAfterSeconds, int limit) {
        super(ErrorCode.RATE_LIMITED, "AI 调用超过限流阈值，请在 " + retryAfterSeconds + " 秒后重试");
        this.retryAfterSeconds = Math.max(1, retryAfterSeconds);
        this.limit = limit;
    }

    public long getRetryAfterSeconds() { return retryAfterSeconds; }
    public int getLimit() { return limit; }
}
