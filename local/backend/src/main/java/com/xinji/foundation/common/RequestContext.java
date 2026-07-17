package com.xinji.foundation.common;

import org.slf4j.MDC;

public final class RequestContext {
    private RequestContext() {}
    public static String requestId() { return MDC.get("requestId"); }
}
