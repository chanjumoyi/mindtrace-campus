package com.mindline.platform;

/**
 * 多模态模型调用异常。
 */
public class MultimodalException extends RuntimeException {

    private final String errorCode;

    public MultimodalException(String errorCode, String message) {
        super(message);
        this.errorCode = errorCode;
    }

    public MultimodalException(String errorCode, String message, Throwable cause) {
        super(message, cause);
        this.errorCode = errorCode;
    }

    public String getErrorCode() { return errorCode; }
}
