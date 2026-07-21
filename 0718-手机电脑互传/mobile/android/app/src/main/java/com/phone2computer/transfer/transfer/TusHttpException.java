package com.phone2computer.transfer.transfer;

import java.io.IOException;

public final class TusHttpException extends IOException {
    private final int statusCode;

    public TusHttpException(int statusCode, String message) {
        super(message);
        this.statusCode = statusCode;
    }

    public int statusCode() {
        return statusCode;
    }
}
