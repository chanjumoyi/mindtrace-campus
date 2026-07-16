package com.mindline.platform;

/**
 * Agent调用异常。
 */
public class AgentException extends RuntimeException {

    private final String errorCode;

    public AgentException(String errorCode, String message) {
        super(message);
        this.errorCode = errorCode;
    }

    public AgentException(String errorCode, String message, Throwable cause) {
        super(message, cause);
        this.errorCode = errorCode;
    }

    public String getErrorCode() { return errorCode; }
}
