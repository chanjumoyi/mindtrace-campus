package com.xinji.foundation.ai;

import com.xinji.foundation.common.BusinessException;
import com.xinji.foundation.common.ErrorCode;
import java.time.Instant;
import java.util.ArrayDeque;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.stereotype.Component;

@Component
public class SimpleRateLimiter {
    private final Map<String, ArrayDeque<Long>> calls = new ConcurrentHashMap<>();
    public void check(String key, int maxPerMinute) {
        long now = Instant.now().toEpochMilli();
        ArrayDeque<Long> q = calls.computeIfAbsent(key, k -> new ArrayDeque<>());
        synchronized (q) {
            while (!q.isEmpty() && q.peekFirst() < now - 60_000) q.removeFirst();
            if (q.size() >= maxPerMinute) throw new BusinessException(ErrorCode.RATE_LIMITED, "AI 调用过于频繁，请稍后重试");
            q.addLast(now);
        }
    }
}
